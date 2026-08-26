# -*- coding: utf-8 -*-
"""
鹭见 SiteSight · 建筑照片筛选工具

用途：删除"远眺/地平线"照片，只保留俯拍与斜拍建筑的照片，避免远景内容把
三维重建范围撑大、拉低建筑模型精度。

原理：大疆照片 EXIF 记录云台俯仰角（GimbalPitchDegree，向下为负）。
  - 俯拍/斜拍建筑：俯仰角明显向下（如 <= -10°）
  - 远眺/地平线：接近水平甚至朝上（如 > -10°）

用法：
  python filter_building_photos.py <源照片目录> <输出目录> [俯仰角阈值 默认-10]

输出目录必须用英文名（ODM 不支持中文路径）。
"""

import csv
import os
import shutil
import subprocess
import sys

EXIFTOOL = os.environ.get("SITESIGHT_EXIFTOOL", r"D:\WebODM（OpenDroneMap）\ODM\SuperBuild\install\bin\exiftool.exe")


def get_pitches(src_dir):
    """用 exiftool 读取全部 JPG 的云台俯仰角，返回 {文件名: 俯仰角}。"""
    out = subprocess.run(
        [EXIFTOOL, "-csv", "-GimbalPitchDegree", "-n", os.path.join(src_dir, "*.jpg")],
        capture_output=True,
        timeout=300,
    )
    text = out.stdout.decode("utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if not ln.startswith("perl:")]
    start = next((i for i, ln in enumerate(lines) if ln.startswith("SourceFile,")), None)
    if start is None:
        return {}
    pitches = {}
    for row in csv.DictReader(lines[start:]):
        fn = os.path.basename(row.get("SourceFile", ""))
        try:
            pitches[fn] = float(row.get("GimbalPitchDegree", "").strip())
        except (TypeError, ValueError):
            pass
    return pitches


def main():
    if len(sys.argv) < 3:
        print("用法: python filter_building_photos.py <源照片目录> <输出目录> [阈值 默认-10]")
        return 1
    src = sys.argv[1]
    dst = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else -10.0

    if not os.path.isdir(src):
        print("源目录不存在:", src)
        return 1
    os.makedirs(dst, exist_ok=True)

    pitches = get_pitches(src)
    keep, drop = [], []
    for fn, p in pitches.items():
        (keep if p <= threshold else drop).append((fn, p))

    copied = 0
    for fn, _ in keep:
        s = os.path.join(src, fn)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst, fn))
            copied += 1

    print("照片总数: %d" % len(pitches))
    print("保留(俯仰角<=%s): %d 张（已复制 %d）" % (threshold, len(keep), copied))
    print("删除(远眺/水平): %d 张" % len(drop))
    if drop:
        print("删除的俯仰角范围: %.1f ~ %.1f" % (min(p for _, p in drop), max(p for _, p in drop)))
    print("输出目录: %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
