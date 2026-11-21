#!/usr/bin/env python3
"""Render mobile-universal 720x1280@30fps 9:16 horror storybook MP4 with 4-frame Line Boil and sample-locked subtitles."""

from collections import OrderedDict
import argparse
import json
import math
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageSequence

W, H = 720, 1280
FPS = 30
XFADE_SEC = 0.45

TITLE_FONT_PATH = "/System/Library/Fonts/Supplemental/Songti.ttc"
TITLE_FONT_INDEX = 2  # Songti TC Bold
SUB_FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
SUB_FONT_INDEX = 0    # Heiti TC Medium

DEFAULT_MOVE = (1.00, 1.08, 0.00, 0.00, 0.05, -0.05)


def ease_in_out_cubic(p: float) -> float:
    p = max(0.0, min(1.0, p))
    if p < 0.5:
        return 4.0 * p * p * p
    return 1.0 - ((-2.0 * p + 2.0) ** 3) / 2.0


def fmt_srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    hh, ms = divmod(ms, 3600000)
    mm, ms = divmod(ms, 60000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def write_srt(cues: list[dict], out_path: str) -> None:
    lines = []
    for idx, cue in enumerate(cues, 1):
        lines.extend([str(idx), f"{fmt_srt_time(cue['start'])} --> {fmt_srt_time(cue['end'])}", cue["text"], ""])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def render_affine_shot(src_img: Image.Image, zoom: float, pan_x_frac: float, pan_y_frac: float) -> Image.Image:
    sw, sh = src_img.size
    base_scale = min(sw / W, sh / H)
    s = base_scale / zoom
    max_dx = max(0.0, (sw - W * s) * 0.48)
    max_dy = max(0.0, (sh - H * s) * 0.48)
    cx = sw * 0.5 + pan_x_frac * max_dx
    cy = sh * 0.5 + pan_y_frac * max_dy
    tx = cx - s * (W * 0.5)
    ty = cy - s * (H * 0.5)
    return src_img.transform((W, H), Image.AFFINE, (s, 0.0, tx, 0.0, s, ty), resample=Image.BICUBIC)


def build_gothic_scrim() -> tuple[np.ndarray, np.ndarray]:
    y = np.linspace(-1.0, 1.0, H)[:, None]
    x = np.linspace(-1.0, 1.0, W)[None, :]
    r2 = (x * 0.96) ** 2 + (y * 0.90) ** 2
    vig = np.clip((r2 - 0.45) * 0.47, 0.0, 0.45)

    scrim = np.zeros((H, W), dtype=np.float32)
    bot_h = 360
    scrim[H - bot_h :, :] = ((np.linspace(0.0, 1.0, bot_h) ** 1.4) * (155.0 / 255.0))[:, None]
    edge_h = 110
    edge_ramp = (np.linspace(0.0, 1.0, edge_h) ** 1.3) * 0.92
    scrim[H - edge_h :, :] = np.maximum(scrim[H - edge_h :, :], edge_ramp[:, None])
    top_h = 180
    scrim[:top_h, :] = np.maximum(
        scrim[:top_h, :],
        ((np.linspace(1.0, 0.0, top_h) ** 1.6) * (80.0 / 255.0))[:, None],
    )
    alpha = np.clip(np.maximum(vig, scrim), 0.0, 0.92)[:, :, None]
    tint = np.zeros((H, W, 3), dtype=np.float32)
    tint[:, :, 0], tint[:, :, 1], tint[:, :, 2] = 4.0, 7.0, 16.0
    return alpha, tint


def build_title_overlay(title_main: str, title_tag: str) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font_main = ImageFont.truetype(TITLE_FONT_PATH, 44, index=TITLE_FONT_INDEX)
    font_tag = ImageFont.truetype(TITLE_FONT_PATH, 22, index=TITLE_FONT_INDEX)

    for label, fnt, txt in [("title_main", font_main, title_main), ("title_tag", font_tag, title_tag)]:
        tofu = bytes(fnt.getmask("\uffff"))
        bad = [ch for ch in sorted({c for c in txt if c not in "\n "}) if bytes(fnt.getmask(ch)) == tofu]
        if bad:
            raise RuntimeError(f"{label} contains tofu glyph(s) {bad}; fix project.json before rendering.")

    tmp = ImageDraw.Draw(layer)
    b1 = tmp.textbbox((0, 0), title_main, font=font_main, stroke_width=3)
    b2 = tmp.textbbox((0, 0), title_tag, font=font_tag, stroke_width=2)
    x1 = (W - (b1[2] - b1[0])) // 2 - b1[0]
    y1 = (132 - (b1[3] - b1[1]) // 2) - b1[1]
    x2 = (W - (b2[2] - b2[0])) // 2 - b2[0]
    y2 = (190 - (b2[3] - b2[1]) // 2) - b2[1]

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((x1, y1 + 3), title_main, font=font_main, fill=(4, 6, 14, 200), stroke_width=4, stroke_fill=(4, 6, 14, 200))
    sd.text((x2, y2 + 2), title_tag, font=font_tag, fill=(4, 6, 14, 190), stroke_width=3, stroke_fill=(4, 6, 14, 190))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(radius=3.5)))

    d = ImageDraw.Draw(layer)
    d.text((x1, y1), title_main, font=font_main, fill=(239, 236, 230, 255), stroke_width=3, stroke_fill=(11, 18, 38, 255))
    d.text((x2, y2), title_tag, font=font_tag, fill=(217, 167, 96, 255), stroke_width=2, stroke_fill=(11, 18, 38, 255))
    return layer


def build_subtitle_overlay(text: str) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype(SUB_FONT_PATH, 34, index=SUB_FONT_INDEX)
    lines = text.split("\n")
    line_height = 46
    start_y = 1035 - (len(lines) * line_height) // 2

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    draw_tmp = ImageDraw.Draw(layer)
    coords = []
    for idx, line in enumerate(lines):
        bbox = draw_tmp.textbbox((0, 0), line, font=font, stroke_width=3)
        lw = bbox[2] - bbox[0]
        if lw > W - 60:
            raise RuntimeError(f"Subtitle line too wide ({lw}px): {line}")
        lx = (W - lw) // 2 - bbox[0]
        ly = start_y + idx * line_height - bbox[1]
        coords.append((lx, ly, line))
        sdraw.text((lx, ly + 2), line, font=font, fill=(4, 7, 16, 200), stroke_width=4, stroke_fill=(4, 7, 16, 200))

    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(radius=2.8)))
    draw = ImageDraw.Draw(layer)
    for lx, ly, line in coords:
        draw.text((lx, ly), line, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(11, 18, 38, 255))
    return layer


def generate_night_motes(seed: int = 20261125) -> list[dict]:
    rng = np.random.default_rng(seed)
    return [
        {
            "x0": float(rng.uniform(0.05 * W, 0.95 * W)),
            "y0": float(rng.uniform(0.08 * H, 0.85 * H)),
            "vx": float(rng.uniform(-4.5, 5.5)),
            "vy": float(rng.uniform(-11.0, 4.0)),
            "r": float(rng.uniform(1.4, 3.0)),
            "phase": float(rng.uniform(0, 2 * math.pi)),
            "freq": float(rng.uniform(0.4, 1.1)),
            "base_alpha": float(rng.uniform(0.11, 0.24)),
        }
        for _ in range(26)
    ]


def apply_night_motes(arr_float: np.ndarray, t_sec: float, motes: list[dict]) -> None:
    for m in motes:
        x = (m["x0"] + m["vx"] * t_sec + 6.0 * math.sin(0.38 * t_sec + m["phase"])) % W
        y = (m["y0"] + m["vy"] * t_sec) % (H * 0.86)
        alpha = m["base_alpha"] * (0.5 + 0.5 * math.sin(m["freq"] * t_sec + m["phase"]))
        rad = int(math.ceil(m["r"] * 2.1))
        x0, x1 = max(0, int(x) - rad), min(W, int(x) + rad + 1)
        y0, y1 = max(0, int(y) - rad), min(H, int(y) + rad + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        g = np.exp(-1.9 * (((xx - x) ** 2 + (yy - y) ** 2) / (m["r"] ** 2))) * alpha
        arr_float[y0:y1, x0:x1, 0] += g * (186.0 - arr_float[y0:y1, x0:x1, 0]) * 0.75
        arr_float[y0:y1, x0:x1, 1] += g * (196.0 - arr_float[y0:y1, x0:x1, 1]) * 0.75
        arr_float[y0:y1, x0:x1, 2] += g * (210.0 - arr_float[y0:y1, x0:x1, 2]) * 0.75


def composite_rgba_onto_float(arr_float: np.ndarray, overlay_rgba: Image.Image, opacity: float = 1.0) -> None:
    if opacity <= 0.001:
        return
    ov = np.asarray(overlay_rgba, dtype=np.float32)
    a = (ov[:, :, 3:4] / 255.0) * opacity
    arr_float[:] = arr_float * (1.0 - a) + ov[:, :, :3] * a


def build_boil_variants(src_img: Image.Image, seed_base: int, n_variants: int = 4, amp: float = 0.35, wavelength: float = 115.0) -> list[Image.Image]:
    """Generate subtle 4-frame hand-drawn GIF Line Boil displacements."""
    if amp <= 0.01:
        return [src_img]
    arr = np.asarray(src_img, dtype=np.float32)
    sh, sw, _ = arr.shape
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    rng = np.random.default_rng(seed_base)
    variants = []
    for _ in range(n_variants):
        p1, p2, p3, p4 = rng.uniform(0.0, 2.0 * math.pi, 4)
        dx = amp * np.sin(yy / wavelength + p1) * np.cos(xx / (wavelength * 1.3) + p2)
        dy = amp * np.cos(xx / wavelength + p3) * np.sin(yy / (wavelength * 1.3) + p4)
        sx = np.clip(xx + dx, 0.0, sw - 1.001)
        sy = np.clip(yy + dy, 0.0, sh - 1.001)
        x0, y0 = sx.astype(np.int32), sy.astype(np.int32)
        wx, wy = (sx - x0)[:, :, None], (sy - y0)[:, :, None]
        x1, y1 = np.minimum(x0 + 1, sw - 1), np.minimum(y0 + 1, sh - 1)
        warped = (
            arr[y0, x0] * (1.0 - wx) * (1.0 - wy)
            + arr[y0, x1] * wx * (1.0 - wy)
            + arr[y1, x0] * (1.0 - wx) * wy
            + arr[y1, x1] * wx * wy
        )
        variants.append(Image.fromarray(np.clip(warped, 0.0, 255.0).astype(np.uint8), mode="RGB"))
    return variants


def build_drizzle_tile() -> tuple[np.ndarray, np.ndarray]:
    """Build deterministic subtle diagonal rain-streak tile and upper-78% fade mask."""
    tile = Image.new("L", (W, H), 0)
    td = ImageDraw.Draw(tile)
    rng = np.random.default_rng(7711)
    for _ in range(110):
        x = float(rng.uniform(0, W))
        y = float(rng.uniform(0, H))
        ln = float(rng.uniform(16.0, 34.0))
        dx = -ln * 0.16
        dy = ln
        alpha = int(rng.uniform(95, 195))
        for ox in (-W, 0, W):
            for oy in (-H, 0, H):
                td.line([(x + ox, y + oy), (x + ox + dx, y + oy + dy)], fill=alpha, width=1)
    tex = np.asarray(tile, dtype=np.float32) / 255.0
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    upper_fade = np.clip((0.78 - yy) / 0.16, 0.0, 1.0)
    return tex, upper_fade


def build_horror_masks() -> dict[str, np.ndarray]:
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]

    def radial_mask(cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
        return np.exp(-0.5 * (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)).astype(np.float32)

    r2_edge = np.clip(((xx - 0.5) / 0.45) ** 2 + ((yy - 0.48) / 0.42) ** 2 - 0.35, 0.0, 1.0)
    drizzle_tex, drizzle_fade = build_drizzle_tile()
    return {
        "porch_lamp": radial_mask(0.50, 0.25, 0.32, 0.22)[:, :, None],
        "humid_vapor": np.clip(np.exp(-0.5 * ((yy - 0.56) / 0.24) ** 2), 0.0, 1.0)[:, :, None],
        "window_strobe": radial_mask(0.68, 0.34, 0.35, 0.28)[:, :, None],
        "center_glow": radial_mask(0.50, 0.48, 0.34, 0.30)[:, :, None],
        "upper_glow": radial_mask(0.50, 0.32, 0.35, 0.26)[:, :, None],
        "stair_lamp": radial_mask(0.52, 0.22, 0.26, 0.18)[:, :, None],
        "tunnel_edge": r2_edge[:, :, None],
        "drizzle_tex": drizzle_tex,
        "drizzle_fade": drizzle_fade,
        "drizzle_tint": np.array([196.0, 212.0, 228.0], dtype=np.float32)[None, None, :],
        "amber_vec": np.array([1.0, 0.72, 0.34], dtype=np.float32)[None, None, :],
        "crimson_vec": np.array([1.0, 0.18, 0.16], dtype=np.float32)[None, None, :],
        "red_police": np.array([1.0, 0.12, 0.12], dtype=np.float32)[None, None, :],
        "blue_police": np.array([0.16, 0.42, 1.0], dtype=np.float32)[None, None, :],
        "humid_tint": np.array([138.0, 168.0, 132.0], dtype=np.float32)[None, None, :],
    }


def apply_fx_presets(frame: np.ndarray, presets: list[str], t_sec: float, s0: float, s1: float, f_idx: int, masks: dict) -> None:
    dt = t_sec - s0
    span = max(0.1, s1 - s0)

    for fx in presets:
        if fx == "porch_flicker":
            if (f_idx % 59) in (0, 2):
                frame *= 0.94
            frame += (11.0 * (0.5 + 0.5 * math.sin(t_sec * 7.8) * math.cos(t_sec * 2.9))) * masks["porch_lamp"] * masks["amber_vec"]
        elif fx == "humid_mist":
            mist = 0.05 + 0.035 * math.sin(t_sec * 1.15)
            frame += mist * masks["humid_vapor"] * (masks["humid_tint"] - frame * 0.55)
        elif fx == "fine_drizzle":
            sy = int((t_sec * 360.0) % H)
            sx = int((-t_sec * 58.0) % W)
            streaks = np.roll(masks["drizzle_tex"], shift=(sy, sx), axis=(0, 1))
            alpha = (0.12 * streaks * masks["drizzle_fade"])[:, :, None]
            frame += alpha * (masks["drizzle_tint"] - frame)
        elif fx == "police_strobe":
            st = math.sin(t_sec * 8.2)
            if st > 0.15:
                frame += (22.0 * (st - 0.15)) * masks["window_strobe"] * masks["red_police"]
            elif st < -0.15:
                frame += (22.0 * (-st - 0.15)) * masks["window_strobe"] * masks["blue_police"]
        elif fx == "flashlight_dread":
            frame *= 1.0 - (0.18 + 0.16 * min(1.0, dt / span)) * masks["tunnel_edge"]
            frame += (14.0 * (0.5 + 0.5 * math.sin(dt * 1.7))) * masks["center_glow"]
        elif fx == "crimson_pulse":
            frame += (16.0 * (0.5 + 0.5 * math.sin(t_sec * 2.4))) * masks["upper_glow"] * masks["crimson_vec"]
            frame *= 1.0 - 0.22 * masks["tunnel_edge"]
        elif fx == "stair_flicker":
            if (f_idx % 73) in (0, 2, 5):
                frame *= 0.93
            frame += (10.0 * (0.5 + 0.5 * math.sin(t_sec * 6.1))) * masks["stair_lamp"] * masks["amber_vec"]
        elif fx == "incense_glow":
            frame += (14.0 * (0.5 + 0.5 * math.sin(t_sec * 1.45))) * masks["center_glow"] * masks["amber_vec"]
            frame *= 1.0 - 0.18 * masks["tunnel_edge"]
        elif fx == "camera_flash":
            if abs(dt - span * 0.52) < 0.035:
                frame += 110.0
        elif fx == "window_bangs":
            for k in range(4):
                db = dt - (span * 0.25 + k * span * 0.17)
                if 0.0 <= db < 0.09:
                    frame += 20.0 if db < 0.03 else -12.0
        elif fx == "closing_vignette":
            prog = min(1.0, dt / max(0.5, span - 0.7))
            frame *= 1.0 - 0.62 * prog * masks["tunnel_edge"]

    np.clip(frame, 0.0, 255.0, out=frame)


class AnimatedShotCache:
    """Lightweight 2-shot LRU cache for true AI animations (_anim.mp4) and loop fallbacks (_loop.mp4 / .gif)."""

    def __init__(self, proj_dir: str, max_entries: int = 2) -> None:
        self.proj_dir = proj_dir
        self.max_entries = max_entries
        self._cache: OrderedDict[str, tuple[str, object]] = OrderedDict()

    def find_source(self, sid: str) -> tuple[str, str] | None:
        anim_p = os.path.join(self.proj_dir, "shots", f"{sid}_anim.mp4")
        if os.path.exists(anim_p):
            return ("anim_mp4", anim_p)
        mp4_p = os.path.join(self.proj_dir, "shots", f"{sid}_loop.mp4")
        if os.path.exists(mp4_p):
            return ("loop_mp4", mp4_p)
        gif_p = os.path.join(self.proj_dir, "shots", f"{sid}.gif")
        if os.path.exists(gif_p):
            return ("gif", gif_p)
        return None

    def _decode_mp4_array(self, path: str, target_fps: int) -> np.ndarray:
        raw = subprocess.check_output([
            "ffmpeg", "-v", "error", "-i", path, "-an",
            "-vf", f"fps={target_fps},scale=768:1376:force_original_aspect_ratio=increase,crop=768:1376",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ])
        frame_bytes = 768 * 1376 * 3
        n = len(raw) // frame_bytes
        if n <= 0:
            raise RuntimeError(f"Decoded 0 frames from animated shot: {path}")
        return np.frombuffer(raw[: n * frame_bytes], dtype=np.uint8).reshape((n, 1376, 768, 3)).copy()

    def _load_entry(self, sid: str) -> tuple[str, object] | None:
        src = self.find_source(sid)
        if not src:
            return None
        kind, path = src
        if kind == "anim_mp4":
            return ("anim_mp4", self._decode_mp4_array(path, 24))
        if kind == "loop_mp4":
            arr = self._decode_mp4_array(path, 15)
            return ("loop", [Image.fromarray(arr[i], mode="RGB") for i in range(len(arr))])
        frames: list[Image.Image] = []
        with Image.open(path) as im:
            for fr in ImageSequence.Iterator(im):
                rgb = fr.convert("RGB")
                if rgb.size != (768, 1376):
                    rgb = ImageOps.fit(rgb, (768, 1376), Image.Resampling.LANCZOS)
                frames.append(rgb)
        return ("loop", frames)

    def _get_or_load(self, sid: str) -> tuple[str, object] | None:
        if sid not in self._cache:
            entry = self._load_entry(sid)
            if not entry:
                return None
            self._cache[sid] = entry
            if len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(sid)
        return self._cache[sid]

    @staticmethod
    def _sample_blended(frames_arr: np.ndarray, pos_f: float) -> np.ndarray:
        n = len(frames_arr)
        pos_f = max(0.0, min(float(n - 1), pos_f))
        i0 = int(math.floor(pos_f))
        i1 = min(i0 + 1, n - 1)
        frac = pos_f - i0
        if frac < 1e-4 or i0 == i1:
            return frames_arr[i0].astype(np.float32)
        return frames_arr[i0].astype(np.float32) * (1.0 - frac) + frames_arr[i1].astype(np.float32) * frac

    def get_anim_mp4_frame(self, sid: str, dt_sec: float, span: float) -> tuple[Image.Image, float] | None:
        entry = self._get_or_load(sid)
        if not entry or entry[0] != "anim_mp4":
            return None
        frames_arr: np.ndarray = entry[1]  # type: ignore[assignment]
        n = len(frames_arr)
        clip_dur = n / 24.0
        dt = max(0.0, min(span, dt_sec))

        if span <= clip_dur * 1.45:
            u = dt / max(0.01, span)
            arr_rgb = self._sample_blended(frames_arr, u * (n - 1))
            zoom = 1.00 + 0.03 * ease_in_out_cubic(u)
        else:
            beat_len = span * 0.5
            xf = 0.40
            u1 = max(0.0, min(1.0, dt / beat_len))
            u2 = max(0.0, min(1.0, (dt - beat_len) / beat_len))
            z1 = 1.00 + 0.03 * ease_in_out_cubic(u1)
            z2 = 1.05 + 0.04 * ease_in_out_cubic(u2)

            if dt <= beat_len - xf:
                arr_rgb = self._sample_blended(frames_arr, u1 * (n - 1))
                zoom = z1
            elif dt >= beat_len + xf:
                arr_rgb = self._sample_blended(frames_arr, u2 * (n - 1))
                zoom = z2
            else:
                w = (dt - (beat_len - xf)) / (2.0 * xf)
                w = w * w * (3.0 - 2.0 * w)
                f1 = self._sample_blended(frames_arr, u1 * (n - 1))
                f2 = self._sample_blended(frames_arr, u2 * (n - 1))
                arr_rgb = f1 * (1.0 - w) + f2 * w
                zoom = z1 * (1.0 - w) + z2 * w

        img = Image.fromarray(np.clip(arr_rgb, 0.0, 255.0).astype(np.uint8), mode="RGB")
        return img, zoom

    def get_frame(self, sid: str, dt_sec: float) -> Image.Image | None:
        entry = self._get_or_load(sid)
        if not entry or entry[0] == "anim_mp4":
            return None
        frames: list[Image.Image] = entry[1]  # type: ignore[assignment]
        anim_idx = int(max(0.0, dt_sec) * 15.0) % len(frames)
        return frames[anim_idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render 9:16 mobile-universal horror MP4 and sample-locked SRT.")
    parser.add_argument("project_dir", help="Project directory containing project.json, audio/vo_timeline.json, audio/master_mix.wav, and shots/*.png.")
    args = parser.parse_args()

    proj_dir = args.project_dir
    with open(os.path.join(proj_dir, "project.json"), "r", encoding="utf-8") as f:
        project = json.load(f)
    with open(os.path.join(proj_dir, "audio/vo_timeline.json"), "r", encoding="utf-8") as f:
        timeline = json.load(f)

    master_mix = os.path.join(proj_dir, "audio/master_mix.wav")
    base_name = project["output_basename"]
    out_mp4 = os.path.join(proj_dir, f"{base_name}.mp4")
    out_srt = os.path.join(proj_dir, f"{base_name}.srt")

    total_dur = float(timeline["total_duration"])
    blackout_t = float(timeline["final_blackout_time"])
    shots = timeline["shots"]
    cues = timeline["cues"]
    write_srt(cues, out_srt)
    print(f"Wrote sample-locked SRT: {out_srt} ({len(cues)} cues)")

    cam_moves = project.get("camera_moves", {})
    shot_fx = project.get("shot_fx", {})
    snappy_shots = set(project.get("snappy_cut_shots", [shots[-1]["id"]]))

    boil_cfg = project.get("boil", {})
    boil_amp = float(boil_cfg.get("amp", 0.35))
    boil_wave = float(boil_cfg.get("wavelength", 115.0))
    boil_hold = max(1, int(boil_cfg.get("hold_frames", 6)))

    anim_cache = AnimatedShotCache(proj_dir, max_entries=2)
    animated_ids = [sh["id"] for sh in shots if anim_cache.find_source(sh["id"]) is not None]
    shot_boil = {
        sh["id"]: build_boil_variants(
            Image.open(os.path.join(proj_dir, sh["shot"])).convert("RGB"),
            seed_base=20261125 + idx * 97,
            amp=boil_amp,
            wavelength=boil_wave,
        )
        for idx, sh in enumerate(shots)
        if sh["id"] not in animated_ids
    }
    print(f"Motion config: animated_shots={animated_ids}, boil=(amp={boil_amp}, wave={boil_wave}, hold={boil_hold})")
    sub_overlays = {cue["id"]: build_subtitle_overlay(cue["text"]) for cue in cues}
    title_overlay = build_title_overlay(project["title_main"], project["title_tag"])
    scrim_alpha, scrim_tint = build_gothic_scrim()
    motes = generate_night_motes()
    masks = build_horror_masks()

    n_frames = int(round(total_dur * FPS))
    print(f"Rendering {n_frames} frames ({total_dur:.2f}s @ {FPS}fps, blackout={blackout_t:.2f}s) -> {out_mp4}")

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-i", master_mix,
            "-c:v", "libx264", "-profile:v", "main", "-level", "3.1",
            "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-shortest", "-movflags", "+faststart", out_mp4,
        ],
        stdin=subprocess.PIPE,
    )

    def render_shot_at(shot_idx: int, t_sec: float, f_idx: int) -> np.ndarray:
        sh = shots[shot_idx]
        sid = sh["id"]
        s0, s1 = float(sh["shot_start"]), float(sh["shot_end"])
        span = max(0.1, s1 - s0)

        raw_presets = shot_fx.get(sid, [])
        presets = [raw_presets] if isinstance(raw_presets, str) else list(raw_presets)

        anim_mp4_res = anim_cache.get_anim_mp4_frame(sid, t_sec - s0, span)
        if anim_mp4_res is not None:
            src_variant, beat_zoom = anim_mp4_res
            arr = np.asarray(render_affine_shot(src_variant, beat_zoom, 0.0, 0.0), dtype=np.float32)
        else:
            u = ease_in_out_cubic((t_sec - s0) / span)
            z0, z1, px0, px1, py0, py1 = cam_moves.get(sid, DEFAULT_MOVE)
            z, px, py = z0 + (z1 - z0) * u, px0 + (px1 - px0) * u, py0 + (py1 - py0) * u
            if "window_bangs" in presets:
                for k in range(4):
                    db = (t_sec - s0) - (span * 0.25 + k * span * 0.17)
                    if 0.0 <= db < 0.14:
                        px += 0.008 * math.sin(db * 65.0)
                        py += 0.006 * math.cos(db * 58.0)
            loop_frame = anim_cache.get_frame(sid, t_sec - s0)
            if loop_frame is not None:
                src_variant = loop_frame
            else:
                variants = shot_boil[sid]
                src_variant = variants[(f_idx // boil_hold) % len(variants)]
            arr = np.asarray(render_affine_shot(src_variant, z, px, py), dtype=np.float32)

        apply_fx_presets(arr, presets, t_sec, s0, s1, f_idx, masks)
        return arr

    try:
        for f_idx in range(n_frames):
            t_sec = f_idx / FPS
            if t_sec >= blackout_t:
                frame = np.zeros((H, W, 3), dtype=np.float32)
            else:
                active_idx = next((i for i, sh in enumerate(shots) if t_sec < float(sh["shot_end"])), len(shots) - 1)
                frame = render_shot_at(active_idx, t_sec, f_idx)
                if active_idx > 0:
                    dt = t_sec - float(shots[active_idx]["shot_start"])
                    xfade = 0.10 if shots[active_idx]["id"] in snappy_shots else XFADE_SEC
                    if 0.0 <= dt < xfade:
                        prev_frame = render_shot_at(active_idx - 1, t_sec, f_idx)
                        w_cur = dt / xfade
                        w_cur = w_cur * w_cur * (3.0 - 2.0 * w_cur)
                        frame = prev_frame * (1.0 - w_cur) + frame * w_cur

                apply_night_motes(frame, t_sec, motes)
                frame = frame * (1.0 - scrim_alpha) + scrim_tint * scrim_alpha

                if 0.2 <= t_sec <= 6.5:
                    t_alpha = (t_sec - 0.2) / 0.5 if t_sec < 0.7 else ((6.5 - t_sec) / 0.8 if t_sec > 5.7 else 1.0)
                    composite_rgba_onto_float(frame, title_overlay, opacity=max(0.0, min(1.0, t_alpha)))

                for cue in cues:
                    if float(cue["start"]) <= t_sec <= float(cue["end"]):
                        composite_rgba_onto_float(frame, sub_overlays[cue["id"]], opacity=1.0)
                        break

                if t_sec < 0.35:
                    frame *= t_sec / 0.35

            proc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
            if (f_idx + 1) % 300 == 0 or (f_idx + 1) == n_frames:
                print(f"  rendered {f_idx + 1}/{n_frames} frames ({100.0 * (f_idx + 1) / n_frames:.1f}%)")
    finally:
        if proc.stdin:
            proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg exited with status {ret}")

    print(f"Done! Encoded mobile-ready 9:16 MP4: {out_mp4}")


if __name__ == "__main__":
    main()
