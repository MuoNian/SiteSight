# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · AI 场地分析报告模块

读取 ODM 建模成果（正射影像 / DSM 元数据），结合“反馈记忆 Agent”中的
用户偏好，调用大模型生成中文场地分析简报；未配置 API 时自动降级为
内置模板报告（离线可用）。
"""

import json
import os
import re
import shutil
import subprocess
import urllib.request

from memory_agent import get_relevant_memories, memory_block

# ODM 安装目录（可用环境变量 SITESIGHT_ODMDIR 覆盖）
ODM_DIR = (
    os.environ.get("SITESIGHT_ODMDIR")
    or os.environ.get("ODM_WEB_ODMDIR")
    or r"D:\WebODM（OpenDroneMap）\ODM"
)

# 本地 API 配置文件（不入库），也可用环境变量直接指定
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
USER_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".sitesight", "config.json")


def load_providers():
    """返回 [{"name","base_url","api_key","model"}, ...]，按优先级排列。"""
    providers = []
    # 1) 环境变量（最简单）
    key = os.environ.get("LLM_API_KEY") or os.environ.get("SITESIGHT_API_KEY")
    if key:
        providers.append(
            {
                "name": "env",
                "base_url": os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                "api_key": key,
                "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            }
        )
    # 2) 本地配置文件（设置页写入的用户配置优先，其次安装目录 app/config.json）
    for cfg in (USER_CONFIG_PATH, CONFIG_PATH):
        if os.path.isfile(cfg):
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for p in data.get("providers", []):
                    if p.get("api_key"):
                        providers.append(
                            {
                                "name": p.get("name", "provider"),
                                "base_url": p["base_url"],
                                "api_key": p["api_key"],
                                "model": p.get("model", "gpt-4o-mini"),
                                "max_tokens": p.get("max_tokens", 4096),
                            }
                        )
                break
            except Exception as e:
                print("读取", cfg, "失败：", e)
    return providers


def call_llm_api(prompt):
    """依次尝试所有供应商，返回首个成功的文本；全部失败返回 None。"""
    for p in load_providers():
        payload = json.dumps(
            {
                "model": p["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": p.get("max_tokens", 4096),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            p["base_url"].rstrip("/") + "/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + p["api_key"],
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choice = result["choices"][0]
                content = choice["message"]["content"]
                if content and content.strip():
                    # 部分网关把 max_tokens 当作总预算，会截断长输出；
                    # 若明显不完整则尝试下一个供应商。
                    if choice.get("finish_reason") == "length" and len(content) < 300:
                        print("LLM 输出被截断（%s），尝试下一个供应商" % p.get("name"))
                        continue
                    return content
        except Exception as e:
            print("LLM API error (%s): %s" % (p.get("name"), e))
    return None


def read_odm_metadata(project):
    """从 ODM 成果目录读取正射影像与 DSM 元数据。"""
    meta = {
        "images": 0,
        "ortho_width": 0,
        "ortho_height": 0,
        "resolution": 0,
        "elev_min": 0,
        "elev_max": 0,
        "elev_range": 0,
    }
    images_dir = os.path.join(project, "images")
    if os.path.isdir(images_dir):
        meta["images"] = len(
            [f for f in os.listdir(images_dir) if f.lower().endswith((".jpg", ".jpeg"))]
        )
    # 优先读取项目里的 metadata.json 侧车（本地预生成，含稳健统计，云端无 GDAL 也能用）
    mj = os.path.join(project, "metadata.json")
    if os.path.isfile(mj):
        try:
            with open(mj, "r", encoding="utf-8") as f:
                m = json.load(f)
            for k in (
                "images",
                "ortho_width",
                "ortho_height",
                "resolution",
                "elev_min",
                "elev_max",
                "elev_range",
            ):
                if k in m and m[k] is not None:
                    meta[k] = m[k]
        except Exception:
            pass
    for key, rel in [
        ("ortho", "odm_orthophoto/odm_orthophoto.tif"),
        ("dsm", "odm_dem/dsm.tif"),
    ]:
        if key == "ortho" and meta["ortho_width"]:
            continue
        if key == "dsm" and meta["elev_range"]:
            continue
        fp = os.path.join(project, rel)
        if not os.path.isfile(fp):
            continue
        try:
            gdal = shutil.which("gdalinfo")
            text = ""
            if gdal:
                out = subprocess.run(
                    [gdal, "-mm", fp],
                    capture_output=True,
                    timeout=60,
                )
                text = out.stdout.decode("utf-8", errors="replace")
            elif os.name == "nt" and os.path.isfile(os.path.join(ODM_DIR, "win32env.bat")):
                out = subprocess.run(
                    ["cmd.exe", "/c", "call win32env.bat && gdalinfo -mm " + fp],
                    cwd=ODM_DIR,
                    capture_output=True,
                    timeout=30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                text = out.stdout.decode("utf-8", errors="replace")
            if not text:
                continue
            if key == "ortho":
                m = re.search(r"Size is (\d+),\s*(\d+)", text)
                if m:
                    meta["ortho_width"] = int(m.group(1))
                    meta["ortho_height"] = int(m.group(2))
                m = re.search(r"Pixel Size = \(([\d.+-]+),([\d.+-]+)\)", text)
                if m:
                    meta["resolution"] = round(abs(float(m.group(1))), 4)
            if key == "dsm":
                m = re.search(r"Computed Min/Max=([-\d.]+),([-\d.]+)", text)
                if m:
                    meta["elev_min"] = float(m.group(1))
                    meta["elev_max"] = float(m.group(2))
                else:
                    m = re.search(r"STATISTICS_MINIMUM=([-\d.]+)", text)
                    if m:
                        meta["elev_min"] = float(m.group(1))
                    m = re.search(r"STATISTICS_MAXIMUM=([-\d.]+)", text)
                    if m:
                        meta["elev_max"] = float(m.group(1))
                meta["elev_range"] = round(meta["elev_max"] - meta["elev_min"], 2)
        except Exception:
            pass
    return meta


def generate_template_report(meta):
    """内置模板报告（离线兜底）。"""
    area_px = meta["ortho_width"] * meta["ortho_height"]
    area_m2 = round(area_px * (meta["resolution"] ** 2), 1) if meta["resolution"] > 0 else 0
    area_km2 = round(area_m2 / 1e6, 4)
    lines = [
        "# 场地分析简报",
        "",
        "## 1. 场地概况",
        "",
        "- 📐 影像数量：{} 张".format(meta["images"]),
        "- 🖼️ 正射影像尺寸：{}×{} 像素".format(meta["ortho_width"], meta["ortho_height"]),
        "- 📏 地面分辨率：{} 米/像素".format(meta["resolution"]),
        "- ⛰️ 高程范围：{} ~ {} 米（高差 {} 米）".format(
            meta["elev_min"], meta["elev_max"], meta["elev_range"]
        ),
        "- 🏗️ 估算覆盖面积：约 {} 平方米（{} km²）".format(area_m2, area_km2),
        "",
        "## 2. 地形特征",
        "",
        "- 场地整体高程差 {} 米，{}".format(
            meta["elev_range"],
            "地形相对平坦，适合大规模建设"
            if meta["elev_range"] < 5
            else "地形有一定起伏，建议分台地布局"
            if meta["elev_range"] < 20
            else "地形起伏较大，需重点考虑土方平衡与边坡稳定",
        ),
        "- DSM 点云已生成，可进一步提取坡度分区与汇水分析",
        "",
        "## 3. 建设适宜性评估",
        "",
        "- ✅ 建议优先布局区域：高程较低、坡度<5%的平坦区域",
        "- ⚠️ 避让区域：高程突变带、DSM局部高点（可能为既有建筑或岩石）",
        "",
        "## 4. 风险与注意事项",
        "",
        "- 💧 排水：低洼处易汇水，需复核周边排水走向",
        "- ⛰️ 边坡：高差突变区域需关注土方平衡与边坡稳定",
        "- 🏢 既有构筑物：DSM 局部高点可能是建筑/树木，建议实地核对",
        "",
        "## 5. 下一步建议",
        "",
        "- 导入 SketchUp/Rhino 进行方案草图设计",
        "- 结合地下管网数据做冲突检测",
        "- 建议实地复核关键高程点",
        "- 若需深化：补充土方量测算、日照模拟、排水分析",
        "",
        "## 6. 数据说明",
        "",
        "---",
        "",
        "**免责声明**：本报告由AI自动生成，数据来源于航拍建模的自动解译，仅供参考。实际工程设计须以专业测绘成果和实地勘察为准。",
    ]
    return "\n".join(lines)


def generate_report(project, force=False):
    """
    生成 AI 场地分析报告。
    返回 (content, used_memories)：内容文本 + 本次参考的用户偏好列表。
    """
    report_path = os.path.join(project, "analysis_report.md")
    if not force and os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), []
        except Exception:
            pass

    meta = read_odm_metadata(project)
    context = "面积 高差 坡度 建设 场地分析 高程 正射 地形 " + " ".join(
        str(x)
        for x in [meta["images"], meta["ortho_width"], meta["resolution"], meta["elev_range"]]
    )
    memories = get_relevant_memories(context_text=context)
    prefs = memory_block(memories)

    prompt = """你是建筑与城市规划分析师，正在为一份场地调研报告做专业分析。以下是某场地航拍建模的自动分析请求：

## 场地数据
- 影像数量：{images} 张
- 正射影像尺寸：{width}x{height} 像素
- 地面分辨率：{grd} 米/像素
- 高程范围：{elev_min} ~ {elev_max} 米，高差 {diff} 米
- 处理产物：三维模型、正射影像、DSM、点云

{prefs}

## 任务
生成一份中文"场地分析简报"，按以下六个部分组织：
1. 场地概况（面积估算、场地尺寸、高程范围、影像覆盖度、地面分辨率）
2. 地形特征（高差、坡度分级、可能的洼地/高地，结合高差数字给出坡度判断）
3. 建设适宜性（推荐建设区域、避让区域、理由，按坡度与地形给出具体建议）
4. 风险与注意事项（排水/汇水、边坡稳定、既有构筑物、日照遮挡等）
5. 下一步建议（需补充的数据、可深化的分析方向）
6. 数据说明（本次分析基于哪些数据、局限在哪里）

要求：
- 语言专业但易懂，适合建筑/规划从业者阅读
- 分点、用 emoji、给具体数值
- 若"用户长期偏好"段落不为空，必须优先遵守其中的偏好
- 高程差较大的场地，坡度判断要基于"高差 / 场地尺度"给出，不要凭空写坡度百分比
- 没有实测数据支撑的内容（如日照、土质、水文）要写成"建议进一步核实"，不要编造
- 末尾加"免责声明：本报告由AI自动生成，仅供参考，实地勘察以专业测绘为准"
""".format(
        images=meta["images"],
        width=meta["ortho_width"],
        height=meta["ortho_height"],
        grd=meta["resolution"],
        elev_min=meta["elev_min"],
        elev_max=meta["elev_max"],
        diff=meta["elev_range"],
        prefs=prefs,
    )

    content = call_llm_api(prompt)
    if not content:
        content = generate_template_report(meta)
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass
    return content, memories
