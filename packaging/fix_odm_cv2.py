# -*- coding: utf-8 -*-
"""修复 ODM venv 中 cv2 的绝对路径配置。

opencv-python 安装时会把打包机的绝对路径写入 cv2\config-3.x.py 与 config.py。
ODM 目录被整体复制/重定位后这些路径失效，导致建模时报
"recursion is detected during loading of cv2 binary extensions"。
本脚本把路径改为基于 __file__ 自动计算，适用于任何安装位置。
"""

import os
import sys


def fix(odm_root):
    cv2_dir = os.path.join(odm_root, "venv", "Lib", "site-packages", "cv2")
    cfg_ext = os.path.join(cv2_dir, "config-3.12.py")
    cfg_bin = os.path.join(cv2_dir, "config.py")
    if not os.path.isfile(cfg_ext) or not os.path.isfile(cfg_bin):
        print("未找到 cv2 配置文件，跳过：", cv2_dir)
        return False
    with open(cfg_ext, "w", encoding="utf-8") as f:
        f.write(
            "import os\n"
            "PYTHON_EXTENSIONS_PATHS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "
            "'python-3.12')] + PYTHON_EXTENSIONS_PATHS\n"
        )
    with open(cfg_bin, "w", encoding="utf-8") as f:
        f.write(
            "import os\n"
            "_odm_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "
            "'..', '..', '..', '..'))\n"
            "BINARIES_PATHS = [os.path.join(_odm_root, 'SuperBuild', 'install', 'bin')] + BINARIES_PATHS\n"
        )
    print("已修复 cv2 配置：", cv2_dir)
    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "dist", "SiteSight", "ODM"
    )
    fix(os.path.abspath(target))
