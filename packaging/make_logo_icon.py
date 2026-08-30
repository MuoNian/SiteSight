# -*- coding: utf-8 -*-
"""用用户最终 LOGO 生成应用/安装包图标 sitesight.ico。"""

import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.normpath(
    os.path.join(HERE, "..", "app", "static", "assets", "logo", "logo_transparent.png")
)
OUT = os.path.join(HERE, "assets", "sitesight.ico")


def main():
    img = Image.open(LOGO).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    side = max(w, h)
    pad = int(side * 0.04)
    canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
    canvas.paste(img, ((side + pad * 2 - w) // 2, (side + pad * 2 - h) // 2), img)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    canvas.save(
        OUT,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("sitesight.ico 已生成:", OUT)


if __name__ == "__main__":
    main()
