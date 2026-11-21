#!/usr/bin/env python3
"""Generate sample-locked per-cue narration (1:1 text parity, glyph tofu check, zero subtitle drift)."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
import soundfile as sf

ENDPOINT = "https://openrouter.ai/api/v1/audio/speech"
SAMPLE_RATE = 48000
TITLE_FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
TITLE_FONT_INDEX = 2  # Songti TC Bold
SUB_FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
SUB_FONT_INDEX = 0    # Heiti TC Medium

DEFAULT_INSTRUCTIONS = (
    "Speak in a deeply eerie, low, cold, breathy midnight ghost-storyteller tone "
    "with dark brooding intimacy and crisp, steady pacing. "
    "Drop quieter and more chilling on whispered quotes or eerie revelations—never cheerful, never theatrical."
)


def load_api_keys(key_file: str | None) -> list[str]:
    """Load OpenRouter API keys from OPENROUTER_API_KEY env var and/or --key-file."""
    keys: list[str] = []
    env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if env_key:
        keys.append(env_key)
    if key_file:
        with open(key_file, "r", encoding="utf-8") as f:
            found = re.findall(r"sk-or-v1-[A-Za-z0-9]+", f.read())
        for k in reversed(found):
            if k not in keys:
                keys.append(k)
    if not keys:
        raise RuntimeError(
            "No OpenRouter API key available. Set OPENROUTER_API_KEY environment variable or pass --key-file."
        )
    return keys


def validate_fonts_and_widths(project: dict) -> None:
    """Reject missing/tofu glyphs (.notdef mask match) in titles & subtitles and verify subtitle widths <= 600px."""
    checks = [
        ("Title main", TITLE_FONT_PATH, TITLE_FONT_INDEX, 44, project.get("title_main", "")),
        ("Title tag", TITLE_FONT_PATH, TITLE_FONT_INDEX, 22, project.get("title_tag", "")),
        (
            "Subtitles",
            SUB_FONT_PATH,
            SUB_FONT_INDEX,
            34,
            "".join(c["text"] for sc in project["scenes"] for c in sc["cues"]),
        ),
    ]
    for label, fpath, fidx, fsz, text in checks:
        font = ImageFont.truetype(fpath, fsz, index=fidx)
        tofu = bytes(font.getmask("\uffff"))
        bad = [ch for ch in sorted({c for c in text if c not in "\n "}) if bytes(font.getmask(ch)) == tofu]
        if bad:
            raise RuntimeError(f"{label} contains unsupported tofu glyph(s) {bad} in {fpath}. Replace characters (e.g. '｜' or '·' instead of '・').")

    sub_font = ImageFont.truetype(SUB_FONT_PATH, 34, index=SUB_FONT_INDEX)
    draw = ImageDraw.Draw(Image.new("RGB", (720, 1280)))
    max_w = 0
    for sc in project["scenes"]:
        for cue in sc["cues"]:
            for line in cue["text"].split("\n"):
                bbox = draw.textbbox((0, 0), line, font=sub_font, stroke_width=3)
                lw = bbox[2] - bbox[0]
                max_w = max(max_w, lw)
                if lw > 600:
                    raise RuntimeError(f"Subtitle line too wide ({lw}px > 600px) in {cue['id']}: {line}")
    print(f"Font tofu check & width check PASSED (max_width={max_w}px <= 600px).")


def count_cjk_chars(text: str) -> int:
    clean = re.sub(r"[\s\n，。！？、：；『』「」]", "", text)
    return max(1, len(clean))


def save_and_wrap_audio(content: bytes, content_type: str, mp3_path: str, wav_raw_path: str) -> None:
    ctype_low = (content_type or "").lower()
    if "audio/pcm" in ctype_low or content[:4] == b"\x00\x00\x00\x00":
        m_rate = re.search(r"rate=(\d+)", ctype_low)
        m_ch = re.search(r"channels=(\d+)", ctype_low)
        rate = int(m_rate.group(1)) if m_rate else 24000
        ch = int(m_ch.group(1)) if m_ch else 1
        with wave.open(wav_raw_path, "wb") as wf:
            wf.setnchannels(ch)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(content)
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", wav_raw_path, "-b:a", "192k", mp3_path],
            check=True,
        )
    else:
        with open(mp3_path, "wb") as f:
            f.write(content)
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_raw_path],
            check=True,
        )


def request_tts(text_input: str, mp3_path: str, wav_raw_path: str, keys: list[str], tts_cfg: dict) -> dict:
    model = tts_cfg.get("model", "google/gemini-3.8-flash-tts")
    voice = tts_cfg.get("voice", "Algenib")
    fallback_voice = tts_cfg.get("fallback_voice", "Enceladus")
    instructions = tts_cfg.get("instructions", DEFAULT_INSTRUCTIONS)

    attempts = [
        {"voice": voice, "instructions": instructions},
        {"voice": voice, "instructions": None},
        {"voice": fallback_voice, "instructions": instructions},
        {"voice": fallback_voice, "instructions": None},
    ]
    last_err = None
    for idx, key in enumerate(keys):
        for cfg in attempts:
            payload = {"model": model, "input": text_input, "voice": cfg["voice"]}
            if cfg["instructions"]:
                payload["instructions"] = cfg["instructions"]
            try:
                resp = requests.post(
                    ENDPOINT,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=90,
                )
                if resp.status_code == 200 and len(resp.content) > 512:
                    save_and_wrap_audio(resp.content, resp.headers.get("content-type", ""), mp3_path, wav_raw_path)
                    return {"key_idx": idx, "voice": cfg["voice"], "bytes": len(resp.content)}
                last_err = f"HTTP {resp.status_code} ({cfg['voice']}): {resp.text[:180]}"
                if resp.status_code in (401, 402, 403):
                    break
            except Exception as exc:
                last_err = str(exc)
    raise RuntimeError(f"TTS failed across all keys/voices: {last_err}")


def probe_duration(path: str) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def detect_silences(path: str, noise_db: str = "-40dB", min_dur: float = 1.1) -> list[dict]:
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise={noise_db}:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    silences, cur_start = [], None
    for line in res.stderr.splitlines():
        ms = re.search(r"silence_start:\s*([0-9.]+)", line)
        me = re.search(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", line)
        if ms:
            cur_start = float(ms.group(1))
        if me:
            silences.append({
                "start": cur_start if cur_start is not None else 0.0,
                "end": float(me.group(1)),
                "duration": float(me.group(2)),
            })
            cur_start = None
    return silences


def clean_single_cue(raw_wav: str, clean_wav: str) -> None:
    filt = (
        "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-42dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0.04:start_threshold=-42dB,"
        "areverse,"
        "loudnorm=I=-16.5:TP=-2.0:LRA=6"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", raw_wav, "-af", filt, "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", clean_wav],
        check=True,
    )


def synthesize_and_qa_cue(cue: dict, cues_dir: str, keys: list[str], tts_cfg: dict) -> dict:
    cid = cue["id"]
    spoken = cue.get("tts_text") or cue["text"].replace("\n", "").replace("『", "").replace("』", "")
    n_ch = count_cjk_chars(spoken)
    mp3_path = os.path.join(cues_dir, f"{cid}.mp3")
    raw_wav = os.path.join(cues_dir, f"{cid}_raw.wav")
    clean_wav = os.path.join(cues_dir, f"{cid}_clean.wav")

    for attempt in range(1, 4):
        if attempt == 1 and os.path.exists(raw_wav) and os.path.getsize(raw_wav) > 512:
            meta = {"cached": True}
        else:
            meta = request_tts(spoken, mp3_path, raw_wav, keys, tts_cfg)

        clean_single_cue(raw_wav, clean_wav)
        dur = probe_duration(clean_wav)
        per_char = dur / n_ch
        silences = detect_silences(clean_wav, noise_db="-40dB", min_dur=1.1)
        internal_glitch = [s for s in silences if s["start"] > 0.25 and s["end"] < (dur - 0.25)]
        if 0.16 <= per_char <= 0.48 and not internal_glitch:
            return {"id": cid, "dur": dur, "n_ch": n_ch, "per_char": per_char, "attempt": attempt, "meta": meta}
        print(f"[RETRY {cid} {attempt}/3] dur={dur:.2f}s ({per_char:.3f}s/ch), glitch={len(internal_glitch)}")

    raise RuntimeError(f"Cue {cid} failed QA after 3 attempts.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize sample-locked per-cue horror narration from project.json.")
    parser.add_argument("project_dir", help="Project directory containing project.json.")
    parser.add_argument("--key-file", default=None, help="Optional file to read OpenRouter key(s) from if env OPENROUTER_API_KEY is not set.")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent TTS synthesis workers (default: 3).")
    args = parser.parse_args()

    proj_path = os.path.join(args.project_dir, "project.json")
    with open(proj_path, "r", encoding="utf-8") as f:
        project = json.load(f)

    validate_fonts_and_widths(project)
    keys = load_api_keys(args.key_file)
    tts_cfg = project.get("tts", {})
    audio_dir = os.path.join(args.project_dir, "audio")
    cues_dir = os.path.join(audio_dir, "cues")
    os.makedirs(cues_dir, exist_ok=True)

    flat_cues = [cue for sc in project["scenes"] for cue in sc["cues"]]
    print(f"Loaded {len(keys)} key(s). Synthesizing {len(flat_cues)} cues...")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(synthesize_and_qa_cue, c, cues_dir, keys, tts_cfg): c["id"] for c in flat_cues}
        for fut in as_completed(futs):
            r = fut.result()
            print(f"  [OK] {r['id']}: {r['dur']:.2f}s ({r['n_ch']} ch, {r['per_char']:.3f}s/ch, try={r['attempt']})")

    intra_samples = int(round(float(tts_cfg.get("intra_cue_gap_sec", 0.22)) * SAMPLE_RATE))
    inter_samples = int(round(float(tts_cfg.get("inter_scene_gap_sec", 0.45)) * SAMPLE_RATE))
    tail_samples = int(round(float(tts_cfg.get("final_tail_sec", 1.40)) * SAMPLE_RATE))
    intra_gap = np.zeros((intra_samples, 2), dtype=np.float32)
    inter_gap = np.zeros((inter_samples, 2), dtype=np.float32)
    tail_gap = np.zeros((tail_samples, 2), dtype=np.float32)

    chunks, cursor_samples = [], 0
    timeline_scenes, all_shots, all_cues = {}, [], []

    for s_idx, sc in enumerate(project["scenes"]):
        sid = sc["id"]
        if s_idx > 0:
            chunks.append(inter_gap)
            cursor_samples += inter_samples

        scene_shot_start = 0.0 if s_idx == 0 else all_shots[-1]["shot_end"]
        vo_start = cursor_samples / SAMPLE_RATE
        scene_cues = []
        split_time = None

        cues = sc["cues"]
        slots = [c["slot"] for c in cues]
        first_b_idx = next((i for i, sl in enumerate(slots) if sl == "b"), len(cues))

        for c_idx, c_def in enumerate(cues):
            if c_idx > 0:
                gap_start = cursor_samples
                chunks.append(intra_gap)
                cursor_samples += intra_samples
                if c_idx == first_b_idx:
                    split_time = (gap_start + intra_samples * 0.5) / SAMPLE_RATE

            data, _ = sf.read(os.path.join(cues_dir, f"{c_def['id']}_clean.wav"), dtype="float32")
            if data.ndim == 1:
                data = np.stack([data, data], axis=1)

            c_start = cursor_samples / SAMPLE_RATE
            chunks.append(data)
            cursor_samples += len(data)
            c_end = cursor_samples / SAMPLE_RATE

            cue_obj = {
                "id": c_def["id"],
                "scene_id": sid,
                "shot_id": f"{sid}_{c_def['slot']}",
                "text": c_def["text"],
                "start": round(c_start, 4),
                "end": round(c_end, 4),
            }
            scene_cues.append(cue_obj)
            all_cues.append(cue_obj)

        vo_end = cursor_samples / SAMPLE_RATE
        if split_time is None:
            split_time = 0.5 * (scene_shot_start + vo_end)
        end_pad = inter_samples if s_idx < len(project["scenes"]) - 1 else tail_samples
        scene_shot_end = (cursor_samples + end_pad) / SAMPLE_RATE

        all_shots.extend([
            {"id": f"{sid}_a", "scene_id": sid, "shot": f"shots/{sid}_a.png", "shot_start": round(scene_shot_start, 4), "shot_end": round(split_time, 4)},
            {"id": f"{sid}_b", "scene_id": sid, "shot": f"shots/{sid}_b.png", "shot_start": round(split_time, 4), "shot_end": round(scene_shot_end, 4)},
        ])
        timeline_scenes[sid] = {
            "id": sid,
            "vo_start": round(vo_start, 4),
            "vo_end": round(vo_end, 4),
            "vo_duration": round(vo_end - vo_start, 4),
            "shot_start": round(scene_shot_start, 4),
            "shot_end": round(scene_shot_end, 4),
            "cues": scene_cues,
        }

    chunks.append(tail_gap)
    stitched = np.concatenate(chunks, axis=0)
    total_dur = len(stitched) / SAMPLE_RATE

    stitched_tmp = os.path.join(audio_dir, "vo_stitched_tmp.wav")
    vo_full_path = os.path.join(audio_dir, "vo_full.wav")
    sf.write(stitched_tmp, stitched, SAMPLE_RATE, subtype="PCM_16")

    vo_filt = "highpass=f=65,equalizer=f=145:t=q:w=1.2:g=2.8,equalizer=f=6000:t=q:w=1.5:g=1.4,aecho=0.9:0.88:35:0.12"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", stitched_tmp, "-af", vo_filt, "-t", f"{total_dur:.6f}",
            "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", vo_full_path,
        ],
        check=True,
    )
    if os.path.exists(stitched_tmp):
        os.remove(stitched_tmp)

    actual_dur = probe_duration(vo_full_path)
    if abs(actual_dur - total_dur) > 0.01:
        raise RuntimeError(f"vo_full.wav duration mismatch: {actual_dur:.4f}s vs {total_dur:.4f}s")

    timeline = {
        "sample_rate": SAMPLE_RATE,
        "total_duration": round(total_dur, 4),
        "final_blackout_time": round(total_dur - 0.70, 4),
        "scenes": timeline_scenes,
        "scene_order": [s["id"] for s in project["scenes"]],
        "shots": all_shots,
        "cues": all_cues,
    }
    tl_path = os.path.join(audio_dir, "vo_timeline.json")
    with open(tl_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    print(f"Saved sample-locked vo_full.wav ({total_dur:.4f}s, diff={abs(actual_dur-total_dur):.4f}s) & vo_timeline.json")


if __name__ == "__main__":
    main()
