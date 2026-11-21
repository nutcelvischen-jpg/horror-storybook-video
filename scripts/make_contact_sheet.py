#!/usr/bin/env python3
"""Build a labeled 4-column portrait contact sheet from normalized shots/*.png files."""

import argparse
import glob
import math
import os
from PIL import Image, ImageDraw, ImageFont

DEFAULT_ORDER = [
    "s01_a", "s01_b", "s02_a", "s02_b",
    "s03_a", "s03_b", "s04_a", "s04_b",
    "s05_a", "s05_b", "s06_a", "s06_b",
    "s07_a", "s07_b", "s08_a", "s08_b",
]
TILE_W, TILE_H = 270, 480
PAD = 12
COLS = 4


def resolve_shot_names(shots_dir: str, order_arg: str | None) -> list[str]:
    """Resolve ordered shot stems from --order, default 16-shot order, or directory scan."""
    if order_arg:
        return [s.strip().removesuffix(".png") for s in order_arg.split(",") if s.strip()]
    if all(os.path.exists(os.path.join(shots_dir, f"{s}.png")) for s in DEFAULT_ORDER[:4]):
        return DEFAULT_ORDER
    found = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(shots_dir, "s*.png"))
        if os.path.basename(p) != "contact_sheet.png"
    )
    return found or DEFAULT_ORDER


def build_contact_sheet(shots_dir: str, out_path: str, names: list[str]) -> None:
    """Assemble and save a labeled 4-column portrait grid contact sheet."""
    rows = max(1, math.ceil(len(names) / COLS))
    canvas = Image.new(
        "RGB",
        (COLS * TILE_W + (COLS + 1) * PAD, rows * TILE_H + (rows + 1) * PAD),
        (12, 14, 22),
    )
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    except Exception:
        font = ImageFont.load_default()

    for idx, name in enumerate(names):
        r, c = divmod(idx, COLS)
        x0 = PAD + c * (TILE_W + PAD)
        y0 = PAD + r * (TILE_H + PAD)
        shot_path = os.path.join(shots_dir, f"{name}.png")
        if os.path.exists(shot_path):
            im = Image.open(shot_path).convert("RGB").resize((TILE_W, TILE_H), Image.Resampling.LANCZOS)
            canvas.paste(im, (x0, y0))
        else:
            draw.rectangle([x0, y0, x0 + TILE_W, y0 + TILE_H], fill=(40, 20, 20))
        draw.rectangle([x0 + 6, y0 + 6, x0 + 92, y0 + 32], fill=(0, 0, 0))
        draw.text((x0 + 10, y0 + 9), name, fill=(239, 236, 230), font=font)

    canvas.save(out_path)
    print(f"Saved contact sheet: {out_path} ({canvas.size}, {len(names)} slots)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 4-column contact sheet from normalized shots/*.png.")
    parser.add_argument("shots_dir", help="Directory containing shot PNGs (e.g. <project>/shots).")
    parser.add_argument("--out", default=None, help="Output PNG path (default: <shots_dir>/contact_sheet.png).")
    parser.add_argument("--order", default=None, help="Comma-separated shot stems (default: auto s01_a..s08_b).")
    args = parser.parse_args()

    out_path = args.out or os.path.join(args.shots_dir, "contact_sheet.png")
    names = resolve_shot_names(args.shots_dir, args.order)
    build_contact_sheet(args.shots_dir, out_path, names)


if __name__ == "__main__":
    main()
