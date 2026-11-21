#!/usr/bin/env python3
"""Normalize a 9:16 portrait image: trim optional light outer border, crop exact 9:16, resize 768x1376 RGB PNG."""

import argparse
import numpy as np
from PIL import Image


def normalize_shot(src_path: str, dst_path: str) -> None:
    """Trim optional light border, center-crop 9:16, and save as 768x1376 RGB PNG."""
    im = Image.open(src_path).convert("RGB")
    lum = np.array(im).mean(axis=2)
    h, w = lum.shape
    if h <= w:
        raise RuntimeError(f"Expected portrait image (height > width), got {(w, h)} for {src_path}")

    max_trim_x = max(10, int(w * 0.14))
    max_trim_y = max(10, int(h * 0.14))
    mx = min(80, w // 6)
    my = min(80, h // 6)

    top = 0
    while top < max_trim_y and (lum[top, mx : w - mx] > 200).mean() > 0.85:
        top += 1
    bot = h - 1
    while bot > h - 1 - max_trim_y and (lum[bot, mx : w - mx] > 200).mean() > 0.85:
        bot -= 1
    left = 0
    while left < max_trim_x and (lum[my : h - my, left] > 200).mean() > 0.85:
        left += 1
    right = w - 1
    while right > w - 1 - max_trim_x and (lum[my : h - my, right] > 200).mean() > 0.85:
        right -= 1

    has_border = (top > 2) or (left > 2) or (bot < h - 3) or (right < w - 3)
    pad = 10 if has_border else 0
    x0, y0, x1, y1 = left + pad, top + pad, right + 1 - pad, bot + 1 - pad

    cw, ch = x1 - x0, y1 - y0
    target_ratio = 9.0 / 16.0
    if cw / ch > target_ratio:
        new_w = int(round(ch * target_ratio))
        x0 += (cw - new_w) // 2
        x1 = x0 + new_w
    else:
        new_h = int(round(cw / target_ratio))
        y0 += (ch - new_h) // 2
        y1 = y0 + new_h

    cropped = im.crop((x0, y0, x1, y1)).resize((768, 1376), Image.Resampling.LANCZOS)
    cropped.save(dst_path)
    print(
        f"Normalized {src_path} ({w}x{h}) -> {dst_path} (768x1376) "
        f"border={has_border} box=({x0},{y0},{x1},{y1})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a portrait illustration to 768x1376 RGB 9:16 PNG.")
    parser.add_argument("src_path", help="Source screenshot or generated PNG/JPG path.")
    parser.add_argument("dst_png_path", help="Destination normalized 768x1376 PNG path.")
    args = parser.parse_args()
    normalize_shot(args.src_path, args.dst_png_path)


if __name__ == "__main__":
    main()
