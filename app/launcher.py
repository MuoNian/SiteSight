# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · 桌面启动器

启动本地网页服务，并用 pywebview 原生窗口展示界面（看起来像独立软件）。
打包后由安装器放在应用目录；开发时可先安装 pywebview 后直接运行。

说明：服务端 server.py 只依赖 Python 标准库，因此以“线程”方式在同一个
进程内运行（而不是用 sys.executable 另起子进程——那样在 PyInstaller 打包
后会再次打开启动器本身）。安装包因此只含一个 SiteSight.exe。
"""

import os
import sys
import threading
import time
import urllib.request

# 必须在导入 server 之前设置环境变量（server.py 在模块导入时读取这些变量）
os.environ["SITESIGHT_NO_BROWSER"] = "1"

# 打包后 ODM 引擎位于安装目录下的 ODM 文件夹
_bundled_odm = os.path.join(os.path.dirname(sys.executable), "ODM")
if os.path.isdir(_bundled_odm):
    os.environ["SITESIGHT_ODMDIR"] = _bundled_odm

import webview  # noqa: E402
import server  # noqa: E402

PORT = int(os.environ.get("SITESIGHT_PORT", "8765"))
LOCK_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
    "SiteSight", "app.lock",
)


def _pid_alive(pid):
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259  # STILL_ACTIVE
    except Exception:
        return True


def wait_server(timeout=60):
    for _ in range(timeout):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/api/info" % PORT, timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def _acquire_lock():
    """单实例锁：已有实例在运行则提示并退出，返回 False。"""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    old_pid = None
    if os.path.isfile(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                old_pid = int((f.read() or "0").strip())
        except Exception:
            old_pid = None
    if old_pid and _pid_alive(old_pid):
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "鹭见 SiteSight 已在运行，请先关闭正在运行的程序。",
                "鹭见 SiteSight",
                0x10,
            )
        except Exception:
            pass
        return False
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True


def _release_lock():
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            if f.read().strip() == str(os.getpid()):
                os.remove(LOCK_FILE)
    except Exception:
        pass


def main():
    if not _acquire_lock():
        sys.exit(0)
    try:
        threading.Thread(target=server.main, daemon=True, name="sitesight-server").start()
        if not wait_server():
            print("警告：本地服务启动超时，请检查端口 %d 是否被占用" % PORT)
        webview.create_window(
            "鹭见 SiteSight",
            "http://127.0.0.1:%d" % PORT,
            width=1280,
            height=860,
            min_size=(960, 640),
        )
        webview.start()
    except Exception:
        # 无控制台模式下把错误写入日志，便于排查
        import traceback

        try:
            log_dir = os.path.join(
                os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                "SiteSight",
            )
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "error.log"), "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
