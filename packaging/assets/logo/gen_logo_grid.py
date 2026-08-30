# -*- coding: utf-8 -*-
"""生成「鹭见 SiteSight」极简 Logo 变体系列网格（18 个，6x3）。"""

import cairosvg

# 核心主体：驻立白鹭剪影（来自 logo_minimal.svg 方案 A）
HERON = (
    "M108 148 C118 138 130 130 142 128 C148 116 162 114 168 124 "
    "C176 132 174 148 170 162 C166 178 172 192 178 204 "
    "C190 196 210 192 230 194 C248 196 258 202 262 212 "
    "C266 220 258 226 248 224 C232 220 218 228 210 240 "
    "C202 250 190 250 182 242 C172 232 168 216 166 200 "
    "C162 180 156 162 148 152 C140 146 122 150 108 148 Z"
)
LEGS = ["180,240 190,240 192,306 182,306", "212,240 222,240 224,306 214,306"]

INK = "#1C2735"       # 深墨蓝
AMBER = "#C96F2A"     # 琥珀
CREAM = "#F6F4EF"     # 浅米底
SEAL = "#C2403A"      # 印章朱红
GRAY = "#8A97A5"


def tf(s, cx=100, cy=126, ox=187, oy=210):
    return "translate(%g %g) scale(%g)" % (cx - ox * s, cy - oy * s, s)


def heron(s, fill=INK, stroke=None, sw=0, cx=100, cy=126):
    t = tf(s, cx, cy)
    p = '<path d="%s" transform="%s"' % (HERON, t)
    if stroke:
        p += ' fill="none" stroke="%s" stroke-width="%g"' % (stroke, sw)
    else:
        p += ' fill="%s"' % fill
    p += '/>'
    legs = ""
    for leg in LEGS:
        if stroke:
            legs += '<polygon points="%s" transform="%s" fill="none" stroke="%s" stroke-width="%g"/>' % (
                leg, t, stroke, sw)
        else:
            legs += '<polygon points="%s" transform="%s" fill="%s"/>' % (leg, t, fill)
    return p + legs


def icon_solid():
    return heron(0.72)


def icon_line():
    return heron(0.72, stroke=INK, sw=3.2)


def icon_thick():
    return heron(0.72, stroke=INK, sw=8.5)


def icon_double():
    return (heron(0.78)
            + heron(0.58, fill=CREAM))


def icon_circle_neg():
    return ('<circle cx="100" cy="126" r="74" fill="%s"/>' % INK
            + heron(0.60, fill=CREAM, cy=126))


def icon_square_neg():
    return ('<rect x="26" y="52" width="148" height="148" rx="34" fill="%s"/>' % INK
            + heron(0.60, fill=CREAM, cy=126))


def icon_roundel():
    return ('<circle cx="100" cy="126" r="76" fill="none" stroke="%s" stroke-width="3.5"/>' % INK
            + '<circle cx="100" cy="126" r="66" fill="none" stroke="%s" stroke-width="1"/>' % INK
            + heron(0.56, cy=124)
            + '<path d="M66 176 C80 170 94 172 100 178 C106 172 120 170 134 176" fill="none" stroke="%s" stroke-width="2" opacity="0.5"/>' % INK)


def icon_shield():
    return ('<path d="M100 46 C128 62 142 86 142 112 C142 142 118 160 100 170 C82 160 58 142 58 112 C58 86 72 62 100 46 Z" fill="%s"/>' % INK
            + heron(0.52, fill=CREAM, cy=124))


def icon_letter():
    return ('<text x="58" y="158" font-size="86" font-weight="900" fill="%s" font-family="Arial,sans-serif">L</text>'
            % INK
            + heron(0.42, cx=126, cy=116))


def icon_seal():
    return ('<rect x="34" y="58" width="132" height="132" rx="10" fill="none" stroke="%s" stroke-width="7"/>' % SEAL
            + heron(0.52, stroke=SEAL, sw=3.4, cx=94, cy=122)
            + '<text x="138" y="92" font-size="24" font-weight="700" fill="%s" font-family="KaiTi,serif">鹭</text>' % SEAL)


def icon_geo():
    return ('<g fill="%s">' % INK
            + '<polygon points="88,88 104,74 112,90"/>'
            + '<polygon points="98,88 108,82 120,116 106,120"/>'
            + '<polygon points="94,118 130,106 140,134 112,146"/>'
            + '<polygon points="132,110 148,114 138,128"/>'
            + '<rect x="104" y="142" width="5" height="28" rx="2"/>'
            + '<rect x="122" y="140" width="5" height="26" rx="2"/>'
            + '</g>')


def icon_diamond():
    return ('<polygon points="100,44 152,126 100,208 48,126" fill="%s"/>' % INK
            + heron(0.50, fill=CREAM, cy=126))


def icon_round():
    return ('<circle cx="100" cy="126" r="72" fill="none" stroke="%s" stroke-width="7"/>' % INK
            + heron(0.58, stroke=INK, sw=4.5, cy=126)
            + '<circle cx="128" cy="112" r="6" fill="%s"/>' % AMBER)


def icon_moon():
    return ('<circle cx="100" cy="128" r="74" fill="%s"/>' % INK
            + '<g clip-path="url(#moonClip)">'
            + heron(0.66, fill=CREAM, cy=148)
            + '</g>'
            + '<path d="M30 168 H170" stroke="%s" stroke-width="2.5" opacity="0.55"/>' % CREAM)


def icon_crosshair():
    return (heron(0.60, cy=124)
            + '<circle cx="100" cy="126" r="78" fill="none" stroke="%s" stroke-width="2" opacity="0.35"/>' % INK
            + '<g stroke="%s" stroke-width="2.5" stroke-linecap="round">' % INK
            + '<path d="M100 40 V52 M100 200 V212 M14 126 H26 M174 126 H186"/>'
            + '</g>')


def icon_hex():
    return ('<polygon points="100,44 147,72 147,184 100,212 53,184 53,72" fill="%s"/>' % INK
            + heron(0.52, fill=CREAM, cy=126))


def icon_duo():
    return ('<rect x="28" y="54" width="144" height="144" rx="36" fill="%s"/>' % AMBER
            + heron(0.60, fill=INK, cy=126))


def icon_mirror():
    s = 0.56
    top = '<path d="%s" transform="%s" fill="%s"/>' % (HERON, tf(s, cy=106), INK)
    t_m = "translate(%g %g) scale(%g %g) translate(-187 -210)" % (100, 2 * 164 - 106, s, -s)
    bottom = '<path d="%s" transform="%s" fill="%s" opacity="0.28"/>' % (HERON, t_m, INK)
    return top + bottom + '<path d="M26 168 H174" stroke="%s" stroke-width="2.5"/>' % INK


ICONS = [
    ("剪影", icon_solid),
    ("线稿", icon_line),
    ("粗描", icon_thick),
    ("双线", icon_double),
    ("圆·负空间", icon_circle_neg),
    ("方·负空间", icon_square_neg),
    ("圆徽章", icon_roundel),
    ("盾徽", icon_shield),
    ("字母 L", icon_letter),
    ("朱印", icon_seal),
    ("几何", icon_geo),
    ("菱形", icon_diamond),
    ("圆润", icon_round),
    ("半月", icon_moon),
    ("准星", icon_crosshair),
    ("六边形", icon_hex),
    ("双色", icon_duo),
    ("镜像", icon_mirror),
]


def build():
    cols, rows = 6, 3
    cw, ch = 200, 280
    W, H = cols * cw, rows * ch
    cells = []
    for i, (name, fn) in enumerate(ICONS):
        col, row = i % cols, i // cols
        x, y = col * cw, row * ch
        cells.append(
            '<g transform="translate(%d %d)">%s'
            '<text x="100" y="252" text-anchor="middle" font-size="13" fill="%s">%s</text></g>'
            % (x, y, fn(), GRAY, name)
        )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'font-family="\'Microsoft YaHei\',sans-serif">'
        '<rect width="%d" height="%d" fill="%s"/>'
        '<defs><clipPath id="moonClip"><circle cx="100" cy="128" r="74"/></clipPath></defs>'
        % (W, H, W, H, W, H, CREAM)
        + "".join(cells)
        + "</svg>"
    )
    with open("logo_grid.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to="logo_grid.png",
                     output_width=W, output_height=H)
    print("grid written: %dx%d, %d icons" % (W, H, len(ICONS)))


if __name__ == "__main__":
    build()
