# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · 桌面启动器

启动本地网页服务，并用 pywebview 原生窗口展示界面（看起来像独立软件）。
打包后由安装器放在应用目录；开发时可先安装 pywebview 后直接运行。
"""

import os
import subprocess
import sys
import time
import urllib.request

import webview

PORT = int(os.environ.get("SITESIGHT_PORT", "8765"))
BASE = os.path.dirname(os.path.abspath(__file__))


def start_server():
    env = os.environ.copy()
    env["SITESIGHT_NO_BROWSER"] = "1"
    # 打包后 ODM 引擎位于安装目录下的 ODM 文件夹
    bundled_odm = os.path.join(os.path.dirname(sys.executable), "ODM")
    if os.path.isdir(bundled_odm):
        env["SITESIGHT_ODMDIR"] = bundled_odm
    server_py = os.path.join(BASE, "server.py")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, server_py],
        env=env,
        cwd=BASE,
        creationflags=flags,
    )


def wait_server(timeout=60):
    for _ in range(timeout):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/api/info" % PORT, timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    start_server()
    wait_server()
    webview.create_window(
        "鹭见 SiteSight",
        "http://127.0.0.1:%d" % PORT,
        width=1280,
        height=860,
        min_size=(960, 640),
    )
    webview.start()


if __name__ == "__main__":
    main()
