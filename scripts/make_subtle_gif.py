#!/usr/bin/env python3
"""Convert a Google Flow MP4 (or still shot PNG fallback) into a calm seamless ping-pong GIF + 768x1376 _loop.mp4 + 3-frame QC strip."""

import argparse
import json
import math
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 768, 1376
GIF_W, GIF_H = 480, 854
FPS = 15


def probe_video(path: str) -> dict:
    """Return width, height, duration of an input video."""
    res = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(res.stdout)
    st = info["streams"][0]
    dur = float(info["format"]["duration"])
    return {"width": int(st["width"]), "height": int(st["height"]), "duration": dur}


def build_qc_strip(loop_mp4: str, out_qc_png: str, tag: str) -> None:
    """Extract 3 representative frames (start, midpoint peak, late return) into a labeled horizontal QC strip."""
    dur = probe_video(loop_mp4)["duration"]
    samples = [
        ("start", min(0.05, dur * 0.05)),
        ("mid-peak", dur * 0.48),
        ("loop-end", max(0.0, dur * 0.92)),
    ]
    tmp_dir = os.path.dirname(out_qc_png) or "."
    tw, th, pad, lh = 270, 480, 12, 28
    canvas = Image.new("RGB", (3 * tw + 4 * pad, th + lh + 2 * pad), (12, 14, 22))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except Exception:
        font = ImageFont.load_default()

    tmp_files = []
    try:
        for idx, (lbl, ts) in enumerate(samples):
            fp = os.path.join(tmp_dir, f".tmp_qc_{os.getpid()}_{idx}.png")
            tmp_files.append(fp)
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", loop_mp4, "-frames:v", "1", fp],
                check=True,
            )
            im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            x0, y0 = pad + idx * (tw + pad), pad
            canvas.paste(im, (x0, y0))
            draw.text((x0 + 4, y0 + th + 6), f"{tag} | {lbl} ({ts:.2f}s)", fill=(230, 232, 236), font=font)
        canvas.save(out_qc_png)
    finally:
        for fp in tmp_files:
            if os.path.exists(fp):
                os.remove(fp)


def encode_gif_from_loop_mp4(loop_mp4: str, out_gif: str) -> None:
    """Encode a clean two-pass palette 480x854 15fps animated GIF from _loop.mp4."""
    vf = (
        f"fps={FPS},scale={GIF_W}:{GIF_H}:flags=lanczos,"
        "split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=sierra2_4a"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", loop_mp4, "-vf", vf, "-loop", "0", out_gif],
        check=True,
    )


def convert_flow_mp4(raw_mp4: str, out_prefix: str, start: float, dur: float, slow: float) -> None:
    """Convert raw Flow MP4 into seamless ping-pong _loop.mp4 (768x1376), .gif (480x854), and _flow_qc.png."""
    meta = probe_video(raw_mp4)
    if meta["height"] <= meta["width"]:
        raise RuntimeError(f"Flow output must be portrait 9:16 (got {meta['width']}x{meta['height']}): {raw_mp4}")

    raw_dur = meta["duration"]
    safe_start = max(0.0, min(start, max(0.0, raw_dur - 1.2)))
    safe_dur = max(0.8, min(dur, raw_dur - safe_start))

    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    loop_mp4 = f"{out_prefix}_loop.mp4"
    out_gif = f"{out_prefix}.gif"
    out_qc = f"{out_prefix}_flow_qc.png"

    vf = (
        f"fps={FPS},setpts={slow:.4f}*(PTS-STARTPTS),"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS-STARTPTS,"
        "split=2[fwd][rev_in];[rev_in]reverse,setpts=PTS-STARTPTS[rev];"
        f"[fwd][rev]concat=n=2:v=1:a=0,fps={FPS}[v]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{safe_start:.3f}", "-t", f"{safe_dur:.3f}", "-i", raw_mp4,
            "-filter_complex", vf, "-map", "[v]", "-an",
            "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", loop_mp4,
        ],
        check=True,
    )
    encode_gif_from_loop_mp4(loop_mp4, out_gif)
    build_qc_strip(loop_mp4, out_qc, os.path.basename(out_prefix))
    print(f"Created Flow loop: {loop_mp4}, {out_gif}, {out_qc} (src={meta['width']}x{meta['height']}, {raw_dur:.2f}s)")


def make_procedural_loop(png_path: str, out_prefix: str, effect: str) -> None:
    """Fallback procedural 4s 15fps seamless atmospheric cinemagraph loop from a normalized still PNG."""
    base_im = Image.open(png_path).convert("RGB")
    if base_im.size != (W, H):
        base_im = base_im.resize((W, H), Image.Resampling.LANCZOS)
    base = np.asarray(base_im, dtype=np.float32)

    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    loop_mp4 = f"{out_prefix}_loop.mp4"
    out_gif = f"{out_prefix}.gif"
    out_qc = f"{out_prefix}_flow_qc.png"

    n_frames = 60  # 4.0s @ 15fps
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]

    rain_tex = None
    upper_fade = np.clip((0.78 - yy) / 0.16, 0.0, 1.0)
    if effect == "rain":
        tile = Image.new("L", (W, H), 0)
        td = ImageDraw.Draw(tile)
        rng = np.random.default_rng(9104)
        for _ in range(120):
            x, y = float(rng.uniform(0, W)), float(rng.uniform(0, H))
            ln = float(rng.uniform(16.0, 34.0))
            alpha = int(rng.uniform(90, 185))
            for ox in (-W, 0, W):
                for oy in (-H, 0, H):
                    td.line([(x + ox, y + oy), (x + ox - ln * 0.16, y + oy + ln)], fill=alpha, width=1)
        rain_tex = np.asarray(tile, dtype=np.float32) / 255.0

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", loop_mp4,
        ],
        stdin=subprocess.PIPE,
    )
    try:
        for i in range(n_frames):
            ph = 2.0 * math.pi * (i / n_frames)
            fr = base.copy()
            if effect == "rain" and rain_tex is not None:
                sy = int((i / n_frames) * H)
                sx = int((-i / n_frames) * W * 0.16)
                streaks = np.roll(rain_tex, shift=(sy, sx), axis=(0, 1))
                a = (0.14 * streaks * upper_fade)[:, :, None]
                tint = np.array([196.0, 212.0, 228.0], dtype=np.float32)[None, None, :]
                fr += a * (tint - fr)
            elif effect == "mist":
                band = np.exp(-0.5 * ((yy - 0.50) / 0.22) ** 2)
                wave = 0.5 + 0.5 * np.sin(xx * 6.283 + ph + yy * 3.0)
                a = (0.09 * band * wave * upper_fade)[:, :, None]
                mist_col = np.array([175.0, 190.0, 205.0], dtype=np.float32)[None, None, :]
                fr += a * (mist_col - fr)
            elif effect == "ripple":
                dx = xx - 0.50
                dy = (yy - 0.56) * 1.4
                r = np.sqrt(dx * dx + dy * dy)
                mask = np.exp(-0.5 * (r / 0.24) ** 2) * (yy > 0.32)
                ring = np.sin(r * 45.0 - ph) * 0.5 + 0.5
                a = (0.10 * mask * ring * upper_fade)[:, :, None]
                fr += a * (np.array([190.0, 210.0, 225.0], dtype=np.float32)[None, None, :] - fr)
            elif effect == "candle":
                glow = np.exp(-0.5 * (((xx - 0.50) / 0.30) ** 2 + ((yy - 0.45) / 0.26) ** 2))
                pulse = 0.55 + 0.45 * math.sin(ph) * math.cos(2.0 * ph + 0.4)
                fr += (16.0 * pulse * glow)[:, :, None] * np.array([1.0, 0.72, 0.34], dtype=np.float32)[None, None, :]
            proc.stdin.write(np.clip(fr, 0.0, 255.0).astype(np.uint8).tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed generating procedural loop MP4")

    encode_gif_from_loop_mp4(loop_mp4, out_gif)
    build_qc_strip(loop_mp4, out_qc, f"{os.path.basename(out_prefix)}({effect})")
    print(f"Created fallback procedural loop ({effect}): {loop_mp4}, {out_gif}, {out_qc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create calm seamless ping-pong GIF + 768x1376 _loop.mp4 from Flow MP4 or fallback PNG.")
    parser.add_argument("src", help="Raw Flow MP4 path (or PNG path when --from-png is set).")
    parser.add_argument("out_prefix", help="Output prefix path, e.g. <project_dir>/shots/s02_a.")
    parser.add_argument("--start", type=float, default=0.25, help="Start trim seconds for Flow MP4 (default: 0.25).")
    parser.add_argument("--dur", type=float, default=3.2, help="Segment duration seconds before ping-pong (default: 3.2).")
    parser.add_argument("--slow", type=float, default=1.15, help="Slow-down factor (>1 slows motion; default: 1.15).")
    parser.add_argument("--from-png", action="store_true", help="Generate fallback procedural atmospheric loop from PNG instead of Flow MP4.")
    parser.add_argument("--effect", choices=["rain", "mist", "ripple", "candle"], default="mist", help="Fallback effect when --from-png is used.")
    args = parser.parse_args()

    if args.from_png:
        make_procedural_loop(args.src, args.out_prefix, args.effect)
    else:
        convert_flow_mp4(args.src, args.out_prefix, args.start, args.dur, args.slow)


if __name__ == "__main__":
    main()
