#!/usr/bin/env python3
"""Extract native synchronized foley tracks from Google Flow *_anim.mp4 clips into 48kHz stereo WAVs + manifest."""

import argparse
import glob
import json
import math
import os
import re
import subprocess


SAMPLE_RATE = 48000


def has_audio_stream(mp4_path: str) -> bool:
    """Return True if the video file contains at least one audio stream."""
    res = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "json", mp4_path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(res.stdout or "{}")
    return bool(info.get("streams"))


def probe_duration(path: str) -> float:
    """Return media duration in seconds via ffprobe."""
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def measure_volumedetect(wav_path: str) -> tuple[float, float]:
    """Measure mean_volume_db and max_volume_db via ffmpeg volumedetect filter."""
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", wav_path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    m_mean = re.search(r"mean_volume:\s*([+-]?(?:[0-9.]+|inf))\s*dB", res.stderr, re.IGNORECASE)
    m_max = re.search(r"max_volume:\s*([+-]?(?:[0-9.]+|inf))\s*dB", res.stderr, re.IGNORECASE)
    if not m_mean or not m_max:
        raise RuntimeError(f"Failed to parse volumedetect output for {wav_path}")

    def parse_db(raw: str) -> float:
        val = float(raw)
        return -96.0 if not math.isfinite(val) else round(val, 2)

    return parse_db(m_mean.group(1)), parse_db(m_max.group(1))


def extract_flow_audio(project_dir: str, out_dir: str | None = None) -> dict:
    """Scan shots/*_anim.mp4, extract 48kHz stereo PCM WAVs, measure levels, and write flow_audio_manifest.json."""
    proj_abs = os.path.abspath(project_dir)
    shots_dir = os.path.join(proj_abs, "shots")
    target_dir = os.path.abspath(out_dir) if out_dir else os.path.join(proj_abs, "audio", "flow_sfx")
    os.makedirs(target_dir, exist_ok=True)

    anim_paths = sorted(glob.glob(os.path.join(shots_dir, "*_anim.mp4")))
    manifest: dict[str, dict] = {}

    for mp4_path in anim_paths:
        base = os.path.basename(mp4_path)
        sid = base[:-len("_anim.mp4")]
        if not has_audio_stream(mp4_path):
            print(f"  [SKIP] {base}: no audio stream")
            continue

        wav_path = os.path.join(target_dir, f"flow_{sid}.wav")
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", mp4_path, "-vn",
                "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", wav_path,
            ],
            check=True,
        )
        dur = round(probe_duration(wav_path), 4)
        mean_db, max_db = measure_volumedetect(wav_path)
        manifest[sid] = {
            "path": wav_path,
            "duration": dur,
            "mean_volume_db": mean_db,
            "max_volume_db": max_db,
        }
        print(f"  [OK] {sid}: {wav_path} (dur={dur:.3f}s, mean={mean_db:.1f} dB, max={max_db:.1f} dB)")

    manifest_path = os.path.join(target_dir, "flow_audio_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Wrote {manifest_path} ({len(manifest)}/{len(anim_paths)} animated shots with audio).")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract native synchronized foley tracks from Google Flow *_anim.mp4 clips."
    )
    parser.add_argument("project_dir", help="Project directory containing shots/*_anim.mp4.")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional output directory for extracted WAVs and manifest (default: <project_dir>/audio/flow_sfx).",
    )
    args = parser.parse_args()
    extract_flow_audio(args.project_dir, args.out_dir)


if __name__ == "__main__":
    main()
