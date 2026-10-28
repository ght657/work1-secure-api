#!/usr/bin/env python3
"""Render captured command output (evidence/*.txt) as terminal-style PNG
"screenshots" for the report. Uses PIL, no external services."""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
]

BG = (14, 17, 23, 255)          # dark terminal background
FG = (222, 226, 230, 255)       # light text
TITLE_BG = (34, 40, 49, 255)    # title bar
RED = (255, 120, 120, 255)


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_txt_to_png(txt_path, png_path):
    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines:
        lines = ["(empty)"]

    font = load_font(16)
    title_font = load_font(15)
    name = os.path.basename(txt_path)

    # measure
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    line_h = 21
    max_chars = 96
    wrapped = []
    for ln in lines:
        if len(ln) <= max_chars:
            wrapped.append(ln)
        else:
            for i in range(0, len(ln), max_chars):
                wrapped.append(ln[i:i + max_chars])
    width = 16 + max((probe.textlength(w, font=font) for w in wrapped), default=300)
    width = int(min(max(width, 560), 1080) + 40)
    # re-wrap if width is constrained
    max_chars2 = int((width - 40) / (probe.textlength("M", font=font)))
    wrapped = []
    for ln in lines:
        if len(ln) <= max_chars2:
            wrapped.append(ln)
        else:
            for i in range(0, len(ln), max_chars2):
                wrapped.append(ln[i:i + max_chars2])

    title_h = 34
    pad = 16
    height = title_h + pad + len(wrapped) * line_h + pad
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, title_h], fill=TITLE_BG)
    draw.text((14, 8), name, font=title_font, fill=FG)
    y = title_h + pad
    for ln in wrapped:
        color = RED if ("401" in ln and "HTTP" in ln) or "ERROR" in ln.upper() else FG
        draw.text((20, y), ln, font=font, fill=color)
        y += line_h
    img.save(png_path)
    print("rendered", png_path, f"{width}x{height}")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "evidence"
    for txt in sorted(glob.glob(os.path.join(out_dir, "*.txt"))):
        render_txt_to_png(txt, txt[:-4] + ".png")


if __name__ == "__main__":
    main()
