#!/usr/bin/env python3
"""Verify mobile-universal MP4 compliance (ffprobe, faststart, LUFS/dBTP) and extract 8-frame QA contact sheet."""

import argparse
import json
import os
import re
import subprocess
from PIL import Image, ImageDraw, ImageFont


def verify_streams_and_faststart(mp4_path: str) -> dict:
    """Assert H.264 Main L3.1 720x1280@30fps + AAC-LC 48kHz stereo + moov faststart."""
    res = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=codec_type,codec_name,profile,level,width,height,pix_fmt,r_frame_rate,sample_rate,channels",
            "-of", "json", mp4_path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(res.stdout)
    streams = {s["codec_type"]: s for s in info.get("streams", [])}
    v, a = streams.get("video", {}), streams.get("audio", {})

    checks = [
        (v.get("codec_name") == "h264", f"video codec={v.get('codec_name')}"),
        (v.get("profile") == "Main", f"video profile={v.get('profile')}"),
        (str(v.get("level")) == "31", f"video level={v.get('level')}"),
        ((v.get("width"), v.get("height")) == (720, 1280), f"size={v.get('width')}x{v.get('height')}"),
        (v.get("pix_fmt") == "yuv420p", f"pix_fmt={v.get('pix_fmt')}"),
        (v.get("r_frame_rate") == "30/1", f"fps={v.get('r_frame_rate')}"),
        (a.get("codec_name") == "aac", f"audio codec={a.get('codec_name')}"),
        (a.get("profile") == "LC", f"audio profile={a.get('profile')}"),
        (str(a.get("sample_rate")) == "48000", f"sample_rate={a.get('sample_rate')}"),
        (int(a.get("channels", 0)) == 2, f"channels={a.get('channels')}"),
    ]
    failed = [msg for ok, msg in checks if not ok]

    with open(mp4_path, "rb") as f:
        faststart = b"moov" in f.read(256)
    if not faststart:
        failed.append("moov atom not in first 256 bytes (+faststart missing)")

    if failed:
        raise RuntimeError("MP4 stream check FAILED: " + "; ".join(failed))

    fmt = info["format"]
    print(
        f"Stream & faststart PASSED: h264 Main L3.1 720x1280@30fps yuv420p, "
        f"aac LC 48000Hz ch=2, dur={float(fmt['duration']):.3f}s, size={fmt['size']}B, faststart=True"
    )
    return info


def verify_loudness(mp4_path: str) -> tuple[float, float]:
    """Assert Integrated Loudness in [-15.5, -13.5] LUFS and True Peak < -1.0 dBTP."""
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", mp4_path, "-af", "loudnorm=I=-14.5:print_format=summary", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    mi = re.search(r"Input Integrated:\s*([+-]?[0-9.]+)\s*LUFS", res.stderr)
    mp = re.search(r"Input True Peak:\s*([+-]?[0-9.]+)\s*dBTP", res.stderr)
    if not mi or not mp:
        raise RuntimeError("Failed to parse loudnorm summary from ffmpeg output.")
    lufs, dbtp = float(mi.group(1)), float(mp.group(1))
    print(f"Loudness measured: Integrated={lufs:.1f} LUFS, True Peak={dbtp:.1f} dBTP")
    if not (-15.5 <= lufs <= -13.5):
        raise RuntimeError(f"Integrated loudness {lufs:.1f} LUFS outside [-15.5, -13.5] target.")
    if not (dbtp < -1.0):
        raise RuntimeError(f"True Peak {dbtp:.1f} dBTP must be strictly < -1.0 dBTP.")
    print("Loudness & True Peak QA PASSED.")
    return lufs, dbtp


def extract_qa_sheet(mp4_path: str, timeline_path: str, out_sheet: str) -> None:
    """Extract 8 representative timestamps (title, 6 spaced shots, post-blackout) into a 4x2 contact sheet."""
    with open(timeline_path, "r", encoding="utf-8") as f:
        tl = json.load(f)

    shots = tl["shots"]
    cues_by_shot = {}
    for c in tl["cues"]:
        cues_by_shot.setdefault(c["shot_id"], []).append(c)

    pick_indices = sorted({round(i * (len(shots) - 2) / 6) for i in range(1, 7)})[:6]
    timestamps = [("title+" + shots[0]["id"], 2.5)]
    for idx in pick_indices:
        sid = shots[idx]["id"]
        scues = cues_by_shot.get(sid, [])
        ts = 0.5 * (float(scues[0]["start"]) + float(scues[0]["end"])) if scues else 0.5 * (float(shots[idx]["shot_start"]) + float(shots[idx]["shot_end"]))
        timestamps.append((sid, round(ts, 2)))
    timestamps.append(("blackout", round(float(tl["final_blackout_time"]) + 0.35, 2)))

    tmp_dir = os.path.join(os.path.dirname(out_sheet) or ".", "tmp_qa_frames")
    os.makedirs(tmp_dir, exist_ok=True)
    tw, th, pad, label_h, cols, rows = 270, 480, 12, 26, 4, 2
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * (th + label_h) + (rows + 1) * pad), (14, 16, 22))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 15, index=0)

    try:
        for i, (lbl, ts) in enumerate(timestamps[:8]):
            fp = os.path.join(tmp_dir, f"f_{i}.png")
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(ts), "-i", mp4_path, "-frames:v", "1", fp], check=True)
            im = Image.open(fp).convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            r, c = divmod(i, cols)
            x, y = pad + c * (tw + pad), pad + r * (th + label_h + pad)
            sheet.paste(im, (x, y))
            draw.text((x + 4, y + th + 4), f"{lbl} (t={ts:.2f}s)", fill=(230, 232, 236), font=font)
        sheet.save(out_sheet)
        print(f"Saved 8-frame QA contact sheet: {out_sheet} ({sheet.size})")
    finally:
        for fn in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, fn))
        os.rmdir(tmp_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify mobile MP4 compliance and extract 8-frame visual QA sheet.")
    parser.add_argument("mp4_path", help="Rendered output MP4 path.")
    parser.add_argument("timeline_json", help="Sample-locked audio/vo_timeline.json path.")
    parser.add_argument("out_qa_sheet", help="Output 8-frame visual QA PNG path.")
    args = parser.parse_args()

    verify_streams_and_faststart(args.mp4_path)
    verify_loudness(args.mp4_path)
    extract_qa_sheet(args.mp4_path, args.timeline_json, args.out_qa_sheet)


if __name__ == "__main__":
    main()
