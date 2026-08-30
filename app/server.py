# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · 本地网页服务

在浏览器里：选择/拖入照片 -> 开始处理 -> 实时看进度 -> 下载成果
-> AI 场地分析报告 -> 反馈偏好（记忆 Agent）
依赖：仅 Python 标准库（无需安装任何包）
"""

import json
import mimetypes
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import urllib.request
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import memory_agent
from site_report import generate_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

APP_NAME = "鹭见 SiteSight"
APP_VERSION = "1.0.0"
APP_ITERATION = "迭代 2"

# 用户设置存放目录（可写，不会随安装目录变动）
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".sitesight")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")


def _load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


SETTINGS = _load_settings()

# ODM 安装目录（脚本内部已修复过编码问题）
ODM_DIR = (
    os.environ.get("SITESIGHT_ODMDIR")
    or os.environ.get("ODM_WEB_ODMDIR")
    or r"D:\WebODM（OpenDroneMap）\ODM"
)

def _writable_dir(cand):
    """尝试创建目录并写入探测文件，确认真正可写后返回路径。"""
    try:
        os.makedirs(cand, exist_ok=True)
        probe = os.path.join(cand, ".write_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return cand
    except Exception:
        return None


def _default_proj_root():
    """成果目录：优先与程序安装目录一致；不可写时自动回退到用户目录/数据盘。"""
    base = os.path.dirname(BASE_DIR)
    local = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "SiteSight", "SiteSight_Results",
    )
    candidates = [
        os.path.join(base, "SiteSight_Results"),
        local,
        os.path.join("D:", os.sep, "SiteSight_Results"),
        os.path.join("E:", os.sep, "SiteSight_Results"),
        os.path.join(os.path.expanduser("~"), "SiteSight_Results"),
    ]
    for cand in candidates:
        ok = _writable_dir(cand)
        if ok:
            return ok
    return candidates[0]


def _default_temp_dir():
    """临时目录：优先与程序安装目录一致；不可写时回退到用户目录。"""
    base = os.path.dirname(BASE_DIR)
    local = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "SiteSight", "tmp",
    )
    for cand in (os.path.join(base, "tmp"), local):
        ok = _writable_dir(cand)
        if ok:
            return ok
    return local


# 成果目录：可用 SITESIGHT_PROJROOT / ODM_WEB_PROJROOT 覆盖
PROJ_ROOT = (
    os.environ.get("SITESIGHT_PROJROOT")
    or os.environ.get("ODM_WEB_PROJROOT")
    or SETTINGS.get("results_dir")
    or _default_proj_root()
)
TEMP_DIR = SETTINGS.get("temp_dir") or _default_temp_dir()


def apply_settings(results_dir=None, temp_dir=None, providers=None):
    """保存并应用设置（成果目录/临时目录/API 供应商）。"""
    global PROJ_ROOT, TEMP_DIR, SETTINGS
    changed = []
    if results_dir is not None or temp_dir is not None:
        results = (results_dir or PROJ_ROOT).strip()
        temp = (temp_dir or TEMP_DIR).strip()
        for label, d in (("成果目录", results), ("临时目录", temp)):
            if not os.path.isdir(d):
                try:
                    os.makedirs(d, exist_ok=True)
                except Exception:
                    return {"ok": False, "error": "无法创建%s：%s（请检查路径权限）" % (label, d)}
        if results != PROJ_ROOT:
            PROJ_ROOT = results
            SETTINGS["results_dir"] = results
            changed.append("成果目录")
        if temp != TEMP_DIR:
            TEMP_DIR = temp
            SETTINGS["temp_dir"] = temp
            changed.append("临时目录")
    if providers is not None:
        existing = []
        old_cfg = os.path.join(CONFIG_DIR, "config.json")
        if os.path.isfile(old_cfg):
            try:
                with open(old_cfg, "r", encoding="utf-8") as f:
                    existing = json.load(f).get("providers", [])
            except Exception:
                pass
        for p in providers:
            if not p.get("api_key"):
                for e in existing:
                    if e.get("name") == p.get("name") and e.get("api_key"):
                        p["api_key"] = e["api_key"]
                        break
        providers = [p for p in providers if p.get("name") or p.get("api_key")]
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(old_cfg, "w", encoding="utf-8") as f:
            json.dump({"providers": providers}, f, ensure_ascii=False, indent=2)
        SETTINGS["providers"] = providers
        changed.append("API 接入")
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return {"ok": False, "error": "保存设置失败：" + str(e)}
    return {
        "ok": True,
        "changed": changed,
        "results_dir": PROJ_ROOT,
        "temp_dir": TEMP_DIR,
        "note": "成果/临时目录已生效；正在处理中的任务不受影响。",
    }

PORT = int(os.environ.get("SITESIGHT_PORT") or os.environ.get("ODM_WEB_PORT", "8765"))
NO_BROWSER = os.environ.get("SITESIGHT_NO_BROWSER") == "1"

# ODM 处理阶段（用于显示进度）
STAGES = [
    ("dataset", "数据准备"),
    ("split", "分块"),
    ("merge", "合并"),
    ("opensfm", "特征提取与空三"),
    ("openmvs", "稠密点云（最耗时）"),
    ("odm_filterpoints", "点云滤波"),
    ("odm_meshing", "网格生成"),
    ("mvs_texturing", "纹理贴图"),
    ("odm_georeferencing", "地理配准"),
    ("odm_dem", "数字表面模型 DSM"),
    ("odm_orthophoto", "正射影像"),
    ("odm_report", "处理报告"),
    ("odm_postprocess", "收尾"),
]
STAGE_NAMES = [s[0] for s in STAGES]

STATE = {
    "lock": threading.Lock(),
    "running": False,
    "finished": False,
    "success": None,
    "name": None,
    "project": None,
    "log_path": None,
    "start_time": None,
}

OUTPUT_CANDIDATES = [
    ("odm_texturing/odm_textured_model_geo.obj", "三维模型（带纹理）OBJ"),
    ("odm_texturing_25d/odm_textured_model_geo.obj", "三维模型 2.5D OBJ"),
    ("odm_orthophoto/odm_orthophoto.tif", "正射影像 GeoTIFF"),
    ("odm_dem/dsm.tif", "数字表面模型 DSM"),
    ("odm_georeferencing/odm_georeferenced_model.laz", "点云 LAZ"),
    ("odm_meshing/odm_mesh.ply", "网格 PLY"),
    ("odm_report/report.pdf", "处理报告 PDF"),
]

# 官方演示成果（随仓库分发，云端可用）
DEMO_PROJ = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "demo_project"))


def odm_available():
    """判断本机是否可现场建模（需要 Windows + ODM 的 winrun.bat）。"""
    if os.name != "nt":
        return False
    return os.path.isfile(os.path.join(ODM_DIR, "winrun.bat"))


def resolve_project(name):
    """优先返回当前已加载/处理中的项目路径，否则在 PROJ_ROOT 下查找。"""
    if STATE.get("project") and os.path.basename(STATE["project"]) == name:
        if os.path.isdir(STATE["project"]):
            return STATE["project"]
    cand = os.path.join(PROJ_ROOT, name)
    return cand if os.path.isdir(cand) else None


def load_project_state(proj):
    """把某个成果目录加载为当前项目（供分析/下载/报告使用）。"""
    log_path = os.path.join(proj, "processing.log")
    with STATE["lock"]:
        STATE.update(
            running=False,
            finished=True,
            success=True,
            name=os.path.basename(proj),
            project=proj,
            log_path=log_path if os.path.isfile(log_path) else None,
            start_time=None,
        )
    make_preview(proj)
    return os.path.basename(proj)


def read_log_tail(max_lines=40):
    p = STATE.get("log_path")
    if not p or not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def parse_stage(lines):
    """从日志行里找最新的阶段，返回 (中文阶段名, 百分比)"""
    idx = -1
    for ln in lines:
        m = re.search(r"Running (\w+) stage", ln)
        if m and m.group(1) in STAGE_NAMES:
            idx = STAGE_NAMES.index(m.group(1))
        m = re.search(r"Finished (\w+) stage", ln)
        if m and m.group(1) in STAGE_NAMES:
            idx = STAGE_NAMES.index(m.group(1))
    if any("ODM app finished" in ln for ln in lines):
        return "全部完成", 100
    if idx < 0:
        return "正在启动", 2
    return STAGES[idx][1], int((idx + 0.5) / len(STAGES) * 100)


def estimate_eta(elapsed, pct):
    """根据已用时长与进度估算剩余秒数（简单线性外推）。"""
    if not elapsed or not pct or pct <= 2 or pct >= 100:
        return None
    return int(elapsed / pct * (100 - pct))


ERROR_RULES = [
    ("no space left", "磁盘空间不足：请清理磁盘，或在『设置』中把成果目录改到空间更大的盘。"),
    ("disk quota", "磁盘空间不足：请清理磁盘，或在『设置』中把成果目录改到空间更大的盘。"),
    ("memoryerror", "内存不足：请关闭其他占用内存的程序后重试，或改用『快速』精度。"),
    ("out of memory", "内存不足：请关闭其他占用内存的程序后重试，或改用『快速』精度。"),
    ("not enough matches", "照片之间重合度过低：请确保相邻照片重叠率在 60% 以上，或补拍后重试。"),
    ("no matches", "照片特征点不足：请检查照片是否清晰、是否过度曝光，或补拍后重试。"),
    ("camera not supported", "相机型号暂不支持：请先用 EXIF 工具检查照片，或联系开发者。"),
    ("could not find", "找不到所需文件或程序：请检查成果目录与 ODM 引擎是否完整。"),
    ("traceback", "处理过程出现异常：请查看下方日志详情，或重试一次。"),
    ("exception", "处理过程出现异常：请查看下方日志详情，或重试一次。"),
]


def summarize_error(lines):
    """从日志尾部提取错误行，并给出中文原因与建议。"""
    hits = []
    for ln in reversed(lines):
        low = ln.lower()
        if any(k in low for k in ("error", "failed", "traceback", "exception", "abort")):
            hits.append(ln.strip())
        if len(hits) >= 5:
            break
    hits.reverse()
    tip = None
    for kw, msg in ERROR_RULES:
        if any(kw in ln.lower() for ln in hits):
            tip = msg
            break
    if not tip and hits:
        tip = "任务未能成功完成，请对照下方日志检查照片与磁盘空间后重试。"
    return {"lines": hits, "tip": tip}


def status_dict():
    lines = read_log_tail(400)
    stage, pct = parse_stage(lines)
    elapsed = 0
    if STATE.get("start_time"):
        elapsed = int(time.time() - STATE["start_time"])
    d = {
        "running": STATE["running"],
        "finished": STATE["finished"],
        "success": STATE["success"],
        "stage": stage,
        "pct": pct,
        "elapsed": elapsed,
        "eta": estimate_eta(elapsed, pct),
        "name": STATE.get("name"),
        "log": read_log_tail(40),
    }
    if STATE.get("finished") and not STATE.get("success"):
        d["error_summary"] = summarize_error(lines)
    else:
        d["error_summary"] = {"lines": [], "tip": None}
    if STATE.get("project"):
        d["preview"] = "/preview?name=%s" % os.path.basename(STATE["project"])
    return d


def files_dict():
    d = {
        "ok": True,
        "files": [],
        "running": STATE["running"],
        "finished": STATE["finished"],
        "success": STATE["success"],
        "name": STATE.get("name"),
        "has_model": False,
    }
    if not STATE.get("project") or not os.path.isdir(STATE["project"]):
        return d
    for rel, label in OUTPUT_CANDIDATES:
        fp = os.path.join(STATE["project"], rel)
        if os.path.isfile(fp):
            if rel.startswith(("odm_texturing", "odm_meshing", "odm_georeferencing")):
                d["has_model"] = True
            d["files"].append(
                {
                    "label": label,
                    "file": rel.replace(os.sep, "/"),
                    "size_mb": round(os.path.getsize(fp) / 1048576, 1),
                }
            )
    return d


def find_jpg_dir(path):
    for cand in (path, os.path.join(path, "images")):
        if os.path.isdir(cand):
            jpgs = [f for f in os.listdir(cand) if f.lower().endswith((".jpg", ".jpeg"))]
            if jpgs:
                return cand
    return None


def copy_jpgs(src_dir, dest_dir):
    n = 0
    os.makedirs(dest_dir, exist_ok=True)
    for fn in os.listdir(src_dir):
        if fn.lower().endswith((".jpg", ".jpeg")):
            shutil.copy2(os.path.join(src_dir, fn), os.path.join(dest_dir, fn))
            n += 1
    return n


def launch_job(name, make_dsm, make_fast=False, quality="standard"):
    project = os.path.join(PROJ_ROOT, name)
    log_path = os.path.join(project, "processing.log")
    with open(log_path, "w", encoding="utf-8", errors="replace"):
        pass
    logf = open(log_path, "ab")
    env = os.environ.copy()
    env["ODM_NONINTERACTIVE"] = "1"
    args = [
        "cmd.exe",
        "/c",
        os.path.join(ODM_DIR, "winrun.bat"),
        "--project-path",
        PROJ_ROOT,
        name,
    ]
    if quality == "high":
        args.append("--dsm")
        args.append("--pc-quality")
        args.append("high")
    elif quality == "fast":
        args.append("--fast")
    else:
        if make_dsm:
            args.append("--dsm")
        if make_fast:
            args.append("--fast")
    args.append("--optimize-disk-space")
    proc = subprocess.Popen(
        args,
        cwd=ODM_DIR,
        env=env,
        stdout=logf,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    with STATE["lock"]:
        STATE.update(
            running=True,
            finished=False,
            success=None,
            name=name,
            project=project,
            log_path=log_path,
            start_time=time.time(),
        )
    threading.Thread(target=watch_job, args=(proc, log_path), daemon=True).start()


def watch_job(proc, log_path):
    proc.wait()
    ok = proc.returncode == 0
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            if "ODM app finished" in f.read():
                ok = True
    except Exception:
        pass
    with STATE["lock"]:
        STATE["running"] = False
        STATE["finished"] = True
        STATE["success"] = ok
    if ok:
        make_preview(STATE["project"])


def make_preview(project):
    ortho = os.path.join(project, "odm_orthophoto", "odm_orthophoto.tif")
    out = os.path.join(project, "preview_ortho.png")
    if not os.path.exists(ortho):
        return None
    if os.path.exists(out):
        return out
    try:
        gdal_conv = shutil.which("gdal_translate")
        if gdal_conv:
            subprocess.run(
                [gdal_conv, "-of", "PNG", "-outsize", "1400", "0", ortho, out],
                capture_output=True,
                timeout=180,
            )
        elif os.name == "nt" and os.path.isfile(os.path.join(ODM_DIR, "win32env.bat")):
            cmd = "call win32env.bat && gdal_translate -of PNG -outsize 1400 0 {} {}".format(
                ortho, out
            )
            subprocess.run(
                ["cmd.exe", "/c", cmd],
                cwd=ODM_DIR,
                capture_output=True,
                timeout=180,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except Exception:
        pass
    return out if os.path.exists(out) else None


def build_zip(project):
    zpath = os.path.join(project, "全部成果.zip")
    if os.path.exists(zpath):
        return zpath
    dirs = [
        "odm_texturing",
        "odm_texturing_25d",
        "odm_orthophoto",
        "odm_dem",
        "odm_georeferencing",
        "odm_meshing",
        "odm_report",
    ]
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for d in dirs:
            base = os.path.join(project, d)
            if os.path.isdir(base):
                for root, _, files in os.walk(base):
                    for fn in files:
                        fp = os.path.join(root, fn)
                        z.write(fp, os.path.relpath(fp, project))
    return zpath


def export_stl(project):
    """把带纹理 OBJ 转成 STL（3D 打印/模型用）。"""
    obj_path = os.path.join(project, "odm_texturing", "odm_textured_model_geo.obj")
    if not os.path.isfile(obj_path):
        return None
    stl_path = os.path.join(project, "odm_texturing", "odm_textured_model_geo.stl")
    if os.path.isfile(stl_path):
        return stl_path
    try:
        vertices = []
        faces = []
        with open(obj_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "v":
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif parts[0] == "f":
                    idxs = []
                    for p in parts[1:4]:
                        try:
                            idxs.append(int(p.split("/")[0]) - 1)
                        except ValueError:
                            continue
                    if len(idxs) == 3:
                        faces.append(idxs)
        with open(stl_path, "w", encoding="utf-8") as f:
            f.write("solid site_model\n")
            for face in faces:
                v0, v1, v2 = [vertices[i] for i in face]
                ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
                bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
                nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
                norm = (nx * nx + ny * ny + nz * nz) ** 0.5
                if norm > 1e-12:
                    nx, ny, nz = nx / norm, ny / norm, nz / norm
                else:
                    nx, ny, nz = 0, 0, 0
                f.write("  facet normal {} {} {}\n".format(nx, ny, nz))
                f.write("    outer loop\n")
                for vi in face:
                    f.write(
                        "      vertex {} {} {}\n".format(
                            vertices[vi][0], vertices[vi][1], vertices[vi][2]
                        )
                    )
                f.write("    endloop\n")
                f.write("  endfacet\n")
            f.write("endsolid site_model\n")
        return stl_path
    except Exception as e:
        print("STL export error:", e)
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path, download_name=None):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/"):
            ctype += "; charset=utf-8"
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        if download_name:
            self.send_header(
                "Content-Disposition",
                'attachment; filename="{}"'.format(download_name),
            )
        self.end_headers()
        with open(path, "rb") as f:
            while True:
                b = f.read(65536)
                if not b:
                    break
                self.wfile.write(b)

    def _safe_project_path(self, name, rel):
        project = resolve_project(name)
        if not project:
            return None
        project = os.path.realpath(project)
        real = os.path.realpath(os.path.join(project, rel))
        if not real.startswith(project + os.sep):
            return None
        return real

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        if p in ("/", "/index.html"):
            self._serve_file(os.path.join(STATIC_DIR, "index.html"))
        elif p.startswith("/assets/"):
            fp = os.path.realpath(os.path.join(STATIC_DIR, p.lstrip("/")))
            if fp.startswith(os.path.realpath(STATIC_DIR) + os.sep) and os.path.isfile(fp):
                self._serve_file(fp)
            else:
                self.send_error(404)
        elif p.startswith("/data/"):
            rel = p[len("/data/"):]
            data_root = os.path.realpath(os.path.join(os.path.dirname(BASE_DIR), "data"))
            fp = os.path.realpath(os.path.join(data_root, rel))
            if fp.startswith(data_root + os.sep) and os.path.isfile(fp):
                self._serve_file(fp)
            else:
                self.send_error(404)
        elif p == "/api/info":
            self._send_json(
                {
                    "ok": True,
                    "app_name": APP_NAME,
                    "version": APP_VERSION,
                    "iteration": APP_ITERATION,
                    "platform": platform.system(),
                    "odm_available": odm_available(),
                    "demo_project": os.path.isdir(DEMO_PROJ),
                }
            )
        elif p == "/api/status":
            self._send_json(status_dict())
        elif p == "/api/files":
            self._send_json(files_dict())
        elif p == "/api/memories":
            mems = []
            for m in memory_agent.list_memories():
                mems.append(
                    {
                        "id": m.get("id"),
                        "text": m.get("text"),
                        "tags": m.get("tags", []),
                        "created_at": m.get("created_at"),
                        "used_count": m.get("used_count", 0),
                    }
                )
            self._send_json({"ok": True, "memories": mems})
        elif p == "/api/memories/stats":
            self._send_json({"ok": True, "stats": memory_agent.get_stats()})
        elif p == "/download":
            name = q.get("name", [""])[0]
            rel = q.get("file", [""])[0]
            fp = self._safe_project_path(name, rel)
            if fp and os.path.isfile(fp):
                self._serve_file(fp, os.path.basename(fp))
            else:
                self.send_error(404)
        elif p == "/preview":
            name = q.get("name", [""])[0]
            project = resolve_project(name)
            fp = os.path.join(project, "preview_ortho.png") if project else ""
            if os.path.isfile(fp):
                self._serve_file(fp)
            else:
                self.send_error(404)
        elif p == "/api/zip":
            name = q.get("name", [""])[0]
            project = resolve_project(name)
            if not project:
                self.send_error(404)
                return
            # 下载文件名必须用英文（HTTP 头不支持中文）
            self._serve_file(build_zip(project), "SiteSight_Results.zip")
        elif p == "/api/open-folder":
            name = q.get("name", [""])[0]
            project = resolve_project(name)
            if project:
                if os.name == "nt":
                    os.startfile(project)  # type: ignore
                    self._send_json({"ok": True})
                else:
                    self._send_json(
                        {"ok": False, "error": "当前环境不支持打开系统文件夹，请使用下载功能。"}, 400
                    )
            else:
                self._send_json({"ok": False, "error": "项目不存在"}, 404)
        elif p == "/api/analyze":
            name = q.get("name", [""])[0]
            force = q.get("force", ["0"])[0] == "1"
            project = resolve_project(name)
            if not project:
                self.send_error(404)
                return
            if not STATE.get("finished"):
                self._send_json({"ok": False, "error": "处理尚未完成，请等待"}, 400)
                return
            content, used = generate_report(project, force=force)
            self._send_json(
                {
                    "ok": True,
                    "content": content,
                    "preferences": [m.get("text") for m in used],
                }
            )
        elif p == "/api/export":
            name = q.get("name", [""])[0]
            fmt = q.get("format", [""])[0]
            project = resolve_project(name)
            if not project:
                self.send_error(404)
                return
            if not STATE.get("finished"):
                self._send_json({"ok": False, "error": "处理尚未完成，请等待"}, 400)
                return
            fp = None
            if fmt == "stl":
                fp = export_stl(project)
            elif fmt == "ply":
                fp = os.path.join(project, "odm_meshing", "odm_mesh.ply")
            elif fmt == "laz":
                fp = os.path.join(project, "odm_georeferencing", "odm_georeferenced_model.laz")
            if fp and os.path.isfile(fp):
                self._serve_file(fp, os.path.basename(fp))
            else:
                self.send_error(404)
        elif p == "/api/results":
            items = []
            if os.path.isdir(PROJ_ROOT):
                for name in os.listdir(PROJ_ROOT):
                    proj = os.path.join(PROJ_ROOT, name)
                    if not os.path.isdir(proj) or name.startswith("."):
                        continue
                    size = 0
                    for root, _, files in os.walk(proj):
                        for fn in files:
                            try:
                                size += os.path.getsize(os.path.join(root, fn))
                            except OSError:
                                pass
                    items.append(
                        {
                            "name": name,
                            "mtime": os.path.getmtime(proj),
                            "size_mb": round(size / 1048576, 1),
                            "has_model": os.path.isdir(os.path.join(proj, "odm_texturing")),
                            "has_preview": os.path.isfile(os.path.join(proj, "preview_ortho.png")),
                            "running": STATE.get("running") and STATE.get("name") == name,
                        }
                    )
            items.sort(key=lambda d: d["mtime"], reverse=True)
            if os.path.isdir(DEMO_PROJ):
                size = 0
                for root, _, files in os.walk(DEMO_PROJ):
                    for fn in files:
                        try:
                            size += os.path.getsize(os.path.join(root, fn))
                        except OSError:
                            pass
                items.append(
                    {
                        "name": "demo_project",
                        "mtime": os.path.getmtime(DEMO_PROJ),
                        "size_mb": round(size / 1048576, 1),
                        "has_model": os.path.isdir(os.path.join(DEMO_PROJ, "odm_texturing")),
                        "has_preview": os.path.isfile(os.path.join(DEMO_PROJ, "preview_ortho.png")),
                        "running": False,
                        "demo": True,
                    }
                )
            self._send_json({"ok": True, "results": items, "root": PROJ_ROOT})
        elif p == "/api/settings":
            cfg_path = os.path.join(CONFIG_DIR, "config.json")
            providers = []
            for cand in (cfg_path, os.path.join(BASE_DIR, "config.json")):
                if os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as f:
                            providers = json.load(f).get("providers", [])
                        break
                    except Exception:
                        continue
            masked = []
            for pr in providers:
                key = pr.get("api_key", "") or ""
                masked.append(
                    {
                        "name": pr.get("name", ""),
                        "base_url": pr.get("base_url", ""),
                        "model": pr.get("model", ""),
                        "has_key": bool(key),
                        "key_tail": key[-4:] if len(key) > 4 else "",
                    }
                )
            self._send_json(
                {
                    "ok": True,
                    "results_dir": PROJ_ROOT,
                    "temp_dir": TEMP_DIR,
                    "default_results_dir": _default_proj_root(),
                    "providers": masked,
                    "api_configured": any(p["has_key"] for p in masked),
                }
            )
        else:
            self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/new-project":
            with STATE["lock"]:
                if STATE["running"]:
                    self._send_json({"ok": False, "error": "已有任务在运行，请等待完成"}, 400)
                    return
            name = "project_" + time.strftime("%Y%m%d_%H%M%S")
            os.makedirs(os.path.join(PROJ_ROOT, name, "images"), exist_ok=True)
            self._send_json({"ok": True, "name": name})
        elif u.path == "/api/start":
            with STATE["lock"]:
                if STATE["running"]:
                    self._send_json({"ok": False, "error": "已有任务在运行，请等待完成"}, 400)
                    return
            if not odm_available():
                self._send_json(
                    {
                        "ok": False,
                        "error": "当前环境未配置 ODM 建模引擎（云端演示版不支持现场建模）。"
                        "请使用『加载已有成果』或『官方演示』；完整建模请在本机运行。",
                    },
                    400,
                )
                return
            body = self._read_body()
            name = body.get("name") or "project_" + time.strftime("%Y%m%d_%H%M%S")
            photo_path = body.get("path")
            make_dsm = bool(body.get("make_dsm", True))
            make_fast = bool(body.get("make_fast", False))
            quality = body.get("quality", "standard")
            project = os.path.join(PROJ_ROOT, name)
            os.makedirs(os.path.join(project, "images"), exist_ok=True)
            if photo_path:
                src = find_jpg_dir(photo_path)
                if not src:
                    self._send_json(
                        {"ok": False, "error": "该路径下没有 JPG 照片：" + photo_path}, 400
                    )
                    return
                n = copy_jpgs(src, os.path.join(project, "images"))
            else:
                n = len(
                    [
                        f
                        for f in os.listdir(os.path.join(project, "images"))
                        if f.lower().endswith((".jpg", ".jpeg"))
                    ]
                )
            if n < 2:
                self._send_json({"ok": False, "error": "至少需要 2 张 JPG 照片（当前 %d 张）" % n}, 400)
                return
            launch_job(name, make_dsm, make_fast, quality)
            self._send_json({"ok": True, "name": name, "count": n})
        elif u.path == "/api/demo":
            if not os.path.isdir(DEMO_PROJ):
                self._send_json({"ok": False, "error": "演示数据缺失（data/demo_project 不存在）"}, 404)
                return
            name = load_project_state(DEMO_PROJ)
            self._send_json({"ok": True, "name": name, "demo": True})
        elif u.path == "/api/load-project":
            body = self._read_body()
            proj = (body.get("path") or "").strip()
            if not os.path.isdir(proj):
                self._send_json({"ok": False, "error": "文件夹不存在：" + proj}, 400)
                return
            has_ortho = os.path.isfile(os.path.join(proj, "odm_orthophoto", "odm_orthophoto.tif"))
            has_model = os.path.isdir(os.path.join(proj, "odm_texturing"))
            if not (has_ortho or has_model):
                self._send_json(
                    {"ok": False, "error": "这不是有效的 ODM 成果目录（缺少 odm_orthophoto 或 odm_texturing）"}, 400
                )
                return
            name = load_project_state(proj)
            self._send_json({"ok": True, "name": name})
        elif u.path == "/api/feedback":
            body = self._read_body()
            text = body.get("text", "")
            try:
                mem = memory_agent.add_feedback(text)
                self._send_json({"ok": True, "memory": mem})
            except ValueError as e:
                self._send_json({"ok": False, "error": str(e)}, 400)
        elif u.path == "/api/memories/delete":
            body = self._read_body()
            ok = memory_agent.delete_memory(body.get("id", ""))
            self._send_json({"ok": ok})
        elif u.path == "/api/settings":
            body = self._read_body()
            r = apply_settings(
                results_dir=body.get("results_dir"),
                temp_dir=body.get("temp_dir"),
                providers=body.get("providers"),
            )
            self._send_json(r, 200 if r.get("ok") else 400)
        elif u.path == "/api/shutdown":
            self._send_json({"ok": True, "msg": "正在退出…"})
            threading.Timer(0.6, os._exit, args=(0,)).start()
        else:
            self.send_error(404)

    def do_PUT(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        name = q.get("name", [""])[0]
        rel = q.get("rel", [""])[0]
        images = os.path.join(PROJ_ROOT, name, "images")
        if not os.path.isdir(images):
            self.send_error(404)
            return
        base = os.path.basename(unquote(rel))
        if not base:
            self.send_error(400)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        dest = os.path.join(images, base)
        with open(dest, "wb") as f:
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        self._send_json({"ok": True, "saved": base})


def main():
    os.makedirs(PROJ_ROOT, exist_ok=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://127.0.0.1:%d" % PORT
    print("=" * 56)
    print("  鹭见 SiteSight 已启动")
    print("  请在浏览器打开：" + url)
    print("  成果目录：" + PROJ_ROOT)
    print("  关闭本窗口 = 停止服务（已生成的成果不受影响）")
    print("=" * 56)
    if not NO_BROWSER:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
