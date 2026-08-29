# -*- coding: utf-8 -*-
"""生成鹭见 SiteSight 应用图标（等高线 + 琥珀圆点，品牌一致）。"""

import os

from PIL import Image, ImageDraw


def make_icon(size=256):
    img = Image.new("RGBA", (size, size), (28, 39, 53, 255))  # 深墨面板
    d = ImageDraw.Draw(img)
    margin = size * 0.08
    cx, cy = size / 2, size / 2
    r = size * 0.42

    # 等高线（同心波浪环）
    for i, rr in enumerate([r * 0.42, r * 0.62, r * 0.82]):
        width = max(3, size // 60)
        d.ellipse(
            [cx - rr, cy - rr, cx + rr, cy + rr],
            outline=(255, 239, 216, 200),
            width=width,
        )
        # 打断一点，形成“鹭见”的识别特征
        d.pieslice(
            [cx - rr, cy - rr, cx + rr, cy + rr],
            215,
            250,
            fill=(28, 39, 53, 255),
        )

    # 琥珀色“观测点”
    dot_r = r * 0.13
    dx, dy = cx + r * 0.28, cy - r * 0.30
    d.ellipse(
        [dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r],
        fill=(201, 111, 42, 255),
    )

    return img


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(out_dir, exist_ok=True)
    img = make_icon(256)
    png = os.path.join(out_dir, "sitesight.png")
    ico = os.path.join(out_dir, "sitesight.ico")
    img.save(png)
    img.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("图标已生成:", png, ico)


if __name__ == "__main__":
    main()
