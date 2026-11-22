#!/usr/bin/env python3
"""Generate sample-locked single- or multi-voice per-cue narration with role-specific pre-stitch acoustic FX."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import subprocess
import time
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
    "Speak in a deeply eerie, low, cold, breathy midnight Taiwanese ghost-storyteller tone "
    "with dark brooding intimacy and crisp, steady pacing. "
    "Drop quieter and more chilling on whispered quotes or eerie revelations—never cheerful, never theatrical."
)

SUPPORTED_FX = ("narrator", "warehouse_room", "phone_rx", "stall_reverb", "temple_reverb", "hall_far")


def load_api_keys(key_file: str | None) -> list[str]:
    """Load OpenRouter API keys from OPENROUTER_API_KEY env var and/or --key-file without logging secrets."""
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


def count_cjk_chars(text: str) -> int:
    clean = re.sub(r"[\s\n，。！？、：；『』「」…—·｜]", "", text)
    return max(1, len(clean))


def validate_fonts_and_widths(project: dict) -> None:
    """Reject missing/tofu glyphs (.notdef mask match), check <=15 CJK chars/line, max 2 lines, and widths <= 600px."""
    title_main = project.get("title_main", "")
    title_tag = project.get("title_tag", "")
    for label, txt in (("title_main", title_main), ("title_tag", title_tag)):
        if "\u30fb" in txt:
            raise RuntimeError(f"{label} contains unsupported '・' (U+30FB); use '｜' or '·'.")

    checks = [
        ("Title main", TITLE_FONT_PATH, TITLE_FONT_INDEX, 44, title_main),
        ("Title tag", TITLE_FONT_PATH, TITLE_FONT_INDEX, 22, title_tag),
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
            raise RuntimeError(
                f"{label} contains unsupported tofu glyph(s) {bad} in {fpath}. "
                "Replace characters (e.g. '｜' or '·' instead of '・')."
            )

    sub_font = ImageFont.truetype(SUB_FONT_PATH, 34, index=SUB_FONT_INDEX)
    draw = ImageDraw.Draw(Image.new("RGB", (720, 1280)))
    max_w = 0
    max_cjk = 0
    for sc in project["scenes"]:
        for cue in sc["cues"]:
            lines = cue["text"].split("\n")
            if len(lines) > 2:
                raise RuntimeError(f"Cue {cue['id']} exceeds 2 lines ({len(lines)} lines).")
            for line in lines:
                cjk_n = len(re.sub(r"[\s\n，。！？、：；『』「」…—·｜]", "", line))
                max_cjk = max(max_cjk, cjk_n)
                if cjk_n > 15:
                    raise RuntimeError(f"Cue {cue['id']} line exceeds 15 CJK chars ({cjk_n}): {line}")
                bbox = draw.textbbox((0, 0), line, font=sub_font, stroke_width=3)
                lw = bbox[2] - bbox[0]
                max_w = max(max_w, lw)
                if lw > 600:
                    raise RuntimeError(f"Subtitle line too wide ({lw}px > 600px) in {cue['id']}: {line}")
    print(f"Font tofu, CJK count & width check PASSED (max_cjk={max_cjk} <= 15, max_width={max_w}px <= 600px).")


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


def resolve_role_config(cue: dict, tts_cfg: dict) -> dict:
    """Resolve role voice, fallback_voice, instructions, pacing/silence QA thresholds, and FX preset."""
    role = cue.get("role", "narrator")
    roles = tts_cfg.get("roles", {})
    role_cfg = roles.get(role, {}) if isinstance(roles, dict) else {}

    default_noise = "-46dB" if role == "protag_panic" else "-42dB"
    default_min_sil = 1.45 if role == "protag_panic" else 1.15

    return {
        "role": role,
        "model": role_cfg.get("model", tts_cfg.get("model", "google/gemini-3.8-flash-tts")),
        "voice": role_cfg.get("voice", tts_cfg.get("voice", "Algenib")),
        "fallback_voice": role_cfg.get("fallback_voice", tts_cfg.get("fallback_voice", "Enceladus")),
        "instructions": (
            cue.get("instructions")
            or role_cfg.get("instructions")
            or tts_cfg.get("instructions", DEFAULT_INSTRUCTIONS)
        ),
        "max_per_char": float(cue.get("max_per_char", role_cfg.get("max_per_char", tts_cfg.get("max_per_char", 0.48)))),
        "fx": cue.get("fx") or role_cfg.get("fx") or tts_cfg.get("fx", "narrator"),
        "noise_db": str(cue.get("noise_db") or role_cfg.get("noise_db") or default_noise),
        "min_silence_dur": float(cue.get("min_silence_dur", role_cfg.get("min_silence_dur", default_min_sil))),
    }


def request_tts(text_input: str, mp3_path: str, wav_raw_path: str, keys: list[str], role_cfg: dict) -> dict:
    model = role_cfg["model"]
    voice = role_cfg["voice"]
    fallback_voice = role_cfg["fallback_voice"]
    instructions = role_cfg["instructions"]

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
                if resp.status_code == 429:
                    time.sleep(1.5)
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


def detect_silences(path: str, noise_db: str = "-42dB", min_dur: float = 1.15) -> list[dict]:
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


def apply_role_fx(clean_wav: str, fx_wav: str, fx_name: str) -> float:
    """Apply role-specific acoustic FX cleanly BEFORE stitching and clamp tail precisely via -t."""
    clean_data, sr = sf.read(clean_wav, dtype="float32")
    if sr != SAMPLE_RATE:
        raise RuntimeError(f"Expected {SAMPLE_RATE}Hz in {clean_wav}, got {sr}Hz")
    if clean_data.ndim == 1:
        clean_data = np.stack([clean_data, clean_data], axis=1)
    clean_dur = len(clean_data) / SAMPLE_RATE

    if fx_name == "narrator":
        pad_sec, fade_d = 0.06, 0.045
        fx_chain = (
            "highpass=f=65,equalizer=f=145:t=q:w=1.2:g=2.8,equalizer=f=6000:t=q:w=1.5:g=1.4,"
            "aecho=0.9:0.88:35:0.12,loudnorm=I=-16.5:TP=-2.0:LRA=6"
        )
    elif fx_name == "warehouse_room":
        pad_sec, fade_d = 0.16, 0.060
        fx_chain = (
            "highpass=f=75,equalizer=f=240:t=q:w=1.2:g=-1.5,equalizer=f=2400:t=q:w=1.3:g=1.5,lowpass=f=9000,"
            "aecho=0.86:0.82:38|82|140:0.17|0.11|0.06,loudnorm=I=-16.8:TP=-2.0:LRA=6"
        )
    elif fx_name == "phone_rx":
        pad_sec, fade_d = 0.04, 0.030
        fx_chain = (
            "highpass=f=320,lowpass=f=3300,"
            "equalizer=f=1150:t=q:w=1.0:g=3.5,equalizer=f=2300:t=q:w=1.4:g=2.5,"
            "acompressor=threshold=-22dB:ratio=4.5:attack=4:release=45:makeup=2.0,"
            "loudnorm=I=-17.2:TP=-2.0:LRA=5"
        )
    elif fx_name == "stall_reverb":
        pad_sec, fade_d = 0.12, 0.050
        fx_chain = (
            "highpass=f=90,equalizer=f=480:t=q:w=1.5:g=1.8,equalizer=f=2100:t=q:w=1.2:g=1.6,"
            "aecho=0.84:0.80:18|35|58|90:0.22|0.16|0.11|0.06,loudnorm=I=-17.8:TP=-2.0:LRA=7"
        )
    elif fx_name == "temple_reverb":
        pad_sec, fade_d = 0.20, 0.070
        fx_chain = (
            "highpass=f=65,equalizer=f=160:t=q:w=1.1:g=2.2,lowpass=f=6800,"
            "aecho=0.82:0.80:48|105|185:0.20|0.14|0.08,loudnorm=I=-16.2:TP=-2.0:LRA=6"
        )
    elif fx_name == "hall_far":
        pad_sec, fade_d = 0.22, 0.075
        fx_chain = (
            "highpass=f=110,equalizer=f=380:t=q:w=1.2:g=-1.8,lowpass=f=5800,"
            "aecho=0.80:0.78:55|125|210:0.24|0.17|0.10,loudnorm=I=-17.6:TP=-2.0:LRA=6"
        )
    else:
        raise ValueError(f"Unknown fx preset {fx_name!r}; supported: {SUPPORTED_FX}")

    # Pad extra 0.20s so loudnorm lookahead buffering never clips speech or reverb tail, then clamp cleanly.
    extra_pad = np.zeros((int(round((pad_sec + 0.20) * SAMPLE_RATE)), 2), dtype=np.float32)
    padded_in = fx_wav.replace("_fx.wav", "_fxpad_tmp.wav")
    fx_raw_out = fx_wav.replace("_fx.wav", "_fxout_tmp.wav")
    sf.write(padded_in, np.concatenate([clean_data, extra_pad], axis=0), SAMPLE_RATE, subtype="PCM_16")
    target_dur = clean_dur + pad_sec

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", padded_in, "-af", fx_chain, "-t", f"{target_dur:.6f}",
                "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", fx_raw_out,
            ],
            check=True,
        )
        out_data, _ = sf.read(fx_raw_out, dtype="float32")
        if out_data.ndim == 1:
            out_data = np.stack([out_data, out_data], axis=1)
        target_n = int(round(target_dur * SAMPLE_RATE))
        if len(out_data) > target_n:
            out_data = out_data[:target_n].copy()
        elif len(out_data) < target_n:
            out_data = np.concatenate([out_data, np.zeros((target_n - len(out_data), 2), dtype=np.float32)], axis=0)

        fade_in_n = min(int(0.005 * SAMPLE_RATE), len(out_data) // 8)
        fade_out_n = min(int(round(fade_d * SAMPLE_RATE)), len(out_data) // 4)
        out_data[:fade_in_n] *= np.linspace(0.0, 1.0, fade_in_n, dtype=np.float32)[:, None]
        out_data[-fade_out_n:] *= np.linspace(1.0, 0.0, fade_out_n, dtype=np.float32)[:, None]
        sf.write(fx_wav, out_data, SAMPLE_RATE, subtype="PCM_16")
    finally:
        for tmp_p in (padded_in, fx_raw_out):
            if os.path.exists(tmp_p):
                os.remove(tmp_p)

    actual = probe_duration(fx_wav)
    if abs(actual - target_dur) > 0.01:
        raise RuntimeError(f"FX clamp mismatch on {fx_wav}: {actual:.4f}s vs target {target_dur:.4f}s")
    return actual


def synthesize_and_qa_cue(cue: dict, cues_dir: str, keys: list[str], tts_cfg: dict) -> dict:
    cid = cue["id"]
    role_cfg = resolve_role_config(cue, tts_cfg)
    spoken = cue.get("tts_text") or (
        cue["text"].replace("\n", "").replace("『", "").replace("』", "").replace("「", "").replace("」", "")
    )
    n_ch = count_cjk_chars(spoken)
    mp3_path = os.path.join(cues_dir, f"{cid}.mp3")
    raw_wav = os.path.join(cues_dir, f"{cid}_raw.wav")
    clean_wav = os.path.join(cues_dir, f"{cid}_clean.wav")
    fx_wav = os.path.join(cues_dir, f"{cid}_fx.wav")
    meta_path = os.path.join(cues_dir, f"{cid}_meta.json")

    noise_db = role_cfg["noise_db"]
    min_silence_dur = role_cfg["min_silence_dur"]
    max_per_char = role_cfg["max_per_char"]

    for attempt in range(1, 4):
        if attempt == 1 and os.path.exists(raw_wav) and os.path.getsize(raw_wav) > 512:
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
            else:
                meta = {"voice": role_cfg["voice"]}
            meta["cached"] = True
        else:
            meta = request_tts(spoken, mp3_path, raw_wav, keys, role_cfg)
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf, ensure_ascii=False, indent=2)

        clean_single_cue(raw_wav, clean_wav)
        dur = probe_duration(clean_wav)
        per_char = dur / n_ch
        silences = detect_silences(clean_wav, noise_db=noise_db, min_dur=min_silence_dur)
        internal_glitch = [s for s in silences if s["start"] > 0.25 and s["end"] < (dur - 0.25)]
        if 0.16 <= per_char <= max_per_char and not internal_glitch:
            fx_dur = apply_role_fx(clean_wav, fx_wav, role_cfg["fx"])
            return {
                "id": cid,
                "role": role_cfg["role"],
                "voice_used": meta.get("voice", role_cfg["voice"]),
                "fx": role_cfg["fx"],
                "dur": fx_dur,
                "clean_dur": dur,
                "n_ch": n_ch,
                "per_char": per_char,
                "attempt": attempt,
                "meta": meta,
            }
        print(
            f"[RETRY {cid} ({role_cfg['role']}) {attempt}/3] "
            f"dur={dur:.2f}s ({per_char:.3f}s/ch vs max={max_per_char:.2f}), glitch={len(internal_glitch)}"
        )

    raise RuntimeError(f"Cue {cid} ({role_cfg['role']}) failed QA after 3 attempts.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize sample-locked single- or multi-voice horror narration from project.json.")
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

    cue_results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(synthesize_and_qa_cue, c, cues_dir, keys, tts_cfg): c["id"] for c in flat_cues}
        for fut in as_completed(futs):
            r = fut.result()
            cue_results[r["id"]] = r
            print(
                f"  [OK] {r['id']} [{r['role']}|{r['voice_used']}|{r['fx']}]: "
                f"{r['dur']:.2f}s ({r['n_ch']} ch, {r['per_char']:.3f}s/ch, try={r['attempt']})"
            )

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
        slots = [c.get("slot", "a") for c in cues]
        first_b_idx = next((i for i, sl in enumerate(slots) if sl == "b"), len(cues))

        for c_idx, c_def in enumerate(cues):
            if c_idx > 0:
                gap_start = cursor_samples
                chunks.append(intra_gap)
                cursor_samples += intra_samples
                if c_idx == first_b_idx:
                    split_time = (gap_start + intra_samples * 0.5) / SAMPLE_RATE

            fx_wav_path = os.path.join(cues_dir, f"{c_def['id']}_fx.wav")
            data, sr = sf.read(fx_wav_path, dtype="float32")
            if sr != SAMPLE_RATE:
                raise RuntimeError(f"Unexpected sample rate {sr} in {fx_wav_path}; expected {SAMPLE_RATE}.")
            if data.ndim == 1:
                data = np.stack([data, data], axis=1)

            c_start = cursor_samples / SAMPLE_RATE
            chunks.append(data)
            cursor_samples += len(data)
            c_end = cursor_samples / SAMPLE_RATE

            slot = c_def.get("slot", "a")
            res_meta = cue_results[c_def["id"]]
            cue_obj = {
                "id": c_def["id"],
                "scene_id": sid,
                "shot_id": f"{sid}_{slot}",
                "role": res_meta["role"],
                "voice_used": res_meta["voice_used"],
                "fx": res_meta["fx"],
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

    vo_full_path = os.path.join(audio_dir, "vo_full.wav")
    sf.write(vo_full_path, stitched, SAMPLE_RATE, subtype="PCM_16")

    actual_dur = probe_duration(vo_full_path)
    if abs(actual_dur - total_dur) > 0.01:
        raise RuntimeError(f"vo_full.wav duration mismatch: {actual_dur:.4f}s vs {total_dur:.4f}s")

    voices_summary = sorted({c["voice_used"] for c in all_cues})
    timeline = {
        "sample_rate": SAMPLE_RATE,
        "total_duration": round(total_dur, 4),
        "final_blackout_time": round(total_dur - 0.70, 4),
        "voices_used": voices_summary,
        "scenes": timeline_scenes,
        "scene_order": [s["id"] for s in project["scenes"]],
        "shots": all_shots,
        "cues": all_cues,
    }
    tl_path = os.path.join(audio_dir, "vo_timeline.json")
    with open(tl_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    print(f"Saved sample-locked vo_full.wav ({total_dur:.4f}s, diff={abs(actual_dur-total_dur):.4f}s) & vo_timeline.json")
    print(f"Voices used: {voices_summary}")


if __name__ == "__main__":
    main()
