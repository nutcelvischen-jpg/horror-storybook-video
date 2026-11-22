---
name: horror-storybook-video
description: >-
  End-to-end production workflow for turning horror stories, PTT Marvel threads,
  or urban legends into 9:16 European indie dark-storybook animated horror
  shorts combining Google Flow Omni 1.2 Flash true character animation
  (`shots/<sid>_anim.mp4`) with 4-frame GIF Line Boil fallback, sample-locked
  per-cue narration and subtitles, spatial horror sound design, mobile-universal
  MP4 encoding, visual QA, and private Google Drive delivery. 把恐怖故事、
  PTT Marvel 連載或都市傳說製作成 9:16 歐洲暗黑繪本風恐怖短片，支援 Google Flow
  Omni 1.2 Flash 角色真動畫與手繪微顫混剪、零漂移逐句鎖定字幕配音、空間恐怖音效、
  跨手機播放編碼驗證與私人 Google Drive 交付。
---

# Horror Storybook 9:16 Short Film Workflow

Produce mobile-ready vertical (`720x1280 @ 30fps`, `H.264 Main L3.1`, `AAC-LC 48kHz`) dark-storybook horror films featuring **Hybrid/Full True Character Animation** (Google Flow `Omni 1.2 Flash` anchored on locked Start Frames) alongside subtle 4-frame Line Boil fallback, zero subtitle drift, and verified visual/audio quality.

> Keep `SKILL.md` workflow-level. Read [style-bible.md](./references/style-bible.md) before authoring `project.json` or generating images, [horror-sfx-recipes.md](./references/horror-sfx-recipes.md) before writing each project's soundscape script, and [omni-flash-animation.md](./references/omni-flash-animation.md) before animating shots in Google Flow.

---

## Phase 0 — Source Crawl & Story Approval Gate

1. For web threads or multi-part search results (e.g., PTT Marvel links), use the `browser` subagent to open every chapter in chronological order and capture complete body text plus pivotal author comments/edits. Verify visited origins against `BROWSER_HOST_FACTS`.
2. Present to the user BEFORE starting production:
   - Full list of verified source URLs and chronological beat-by-beat summary.
   - 2 ending options when applicable (e.g., **Option A: pure chilling horror linger** vs. **Option B: full documentary epilogue**).
3. Wait for explicit confirmation before generating audio or visuals.

---

## Phase 1 — Project Config & Sample-Locked Multi-Voice TTS

1. Initialize workspace `<project_dir>/{shots,audio/cues,scripts}`.
2. Author `<project_dir>/project.json` following [style-bible.md](./references/style-bible.md):
   - Every cue line `<= 15` CJK characters; 2 lines max; 1:1 literal parity between spoken narration and subtitle text.
   - **Never** use `・` (`U+30FB`) in `title_tag` (`Songti TC Bold` lacks it and renders `□`); use `｜` (`U+FF5C`) or `·` (`U+00B7`).
   - Configure gentle static Line Boil (`"boil": {"amp": 0.35, "wavelength": 115.0, "hold_frames": 6}`) and optional multi-voice `"tts.roles"` map (`narrator`, `boss_room`, `boss_phone`, `protag_casual`, `protag_panic`, `master`, etc.) plus per-cue `"role"` / `"instructions"` (backward-compatible with single-voice `tts.voice` projects).
3. Run per-cue narration synthesis (`OPENROUTER_API_KEY` env var or `--key-file`, never log or print keys):
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/gen_tts_locked.py "<project_dir>"
   ```
   - Checks `Songti TC Bold` & `Heiti TC Medium` glyphs against `.notdef` tofu mask (`\uffff`) and enforces line width `<= 600px`.
   - Calls `google/gemini-3.8-flash-tts` per cue with role voice/fallback + pre-stitch acoustic FX (`narrator`, `warehouse_room`, `phone_rx`, `stall_reverb`, `temple_reverb`, `hall_far`), trims silence (`areverse`), retries outliers up to 3 attempts, clamps tail via `-t`, stitches `audio/vo_full.wav`, and writes `audio/vo_timeline.json`.

---

## Phase 2 — 3-Tier Horror SFX Architecture & Pre-AAC Limiter

1. Read [horror-sfx-recipes.md](./references/horror-sfx-recipes.md) and write `<project_dir>/scripts/make_horror_bgm.py` reading `audio/vo_timeline.json` and `audio/vo_full.wav`.
2. Follow the **3-Tier Horror SFX Architecture**:
   - **Tier 1 — Flow `Omni 1.2 Flash` native synced foley (`0` extra credits)**: Extract synced SFX from animated hero shots via `scripts/extract_flow_audio.py` during Phase 3.5, then re-run `make_horror_bgm.py` before final Phase 4 render so Flow foley ducks cleanly into `audio/master_mix.wav`.
   - **Tier 2 — Higgsfield `seed_audio` CLI**: Use ONLY for static-shot SFX gaps after `higgsfield workspace set <id>` (`higgsfield generate create seed_audio --prompt "..." --format wav --sample_rate 48000 --wait --json`; note no `--duration` flag). Never bypass Cloudflare (`cf-mitigated: challenge`) or CAPTCHAs on Pixabay.
   - **Tier 3 — Procedural Python/FFmpeg beds**: Dissonant sub-drones, 60Hz hum, `1.8s–2.2s` ambient vacuum drop before the core scare, `-13 dB` reverse-reverb whisper shadows, zero-asset foley, and hard silence cut at `final_blackout_time`.
3. End the ffmpeg master `amix` filter chain with `loudnorm=I=-14.0:TP=-2.0:LRA=10,alimiter=limit=0.6310:attack=5:release=50:level=false:latency=true` so AAC inter-sample overshoot stays `< -1.5 dBTP` on the first render.
4. Run `make_horror_bgm.py` (initially with Tier 2/3, and re-run after Phase 3.5 Tier 1 extraction) and verify `audio/master_mix.wav` duration matches `vo_full.wav`.

---

## Phase 3 — 9:16 Illustrations (Google Flow First) & Contact Sheet Gate

1. Read [style-bible.md](./references/style-bible.md) for architecture/cast locks and Hitchcockian psychological-horror substitutions (zero readable text, zero borders/split panels, zero corpses/nooses/gore, dark uncluttered lower 25%).
2. Generate all 16 shots **Google Flow FIRST** (never bypass CAPTCHAs or bot checks):
   - Open ONE clean Flow project (`https://flow.google.com/` -> `Image` -> `Nano Banana 2.1` -> `9:16` -> `1K` -> `x1`, **`0` Flow credits**), sending at most **2 prompts per browser batch** and downloading borderless `1K Original size` frames (all 16 stills remain inside Flow's library for Phase 3.5).
   - **Quota fallbacks ONLY**: Gemini Web (`9:16`, 4x4 batches, `801x1011` lightbox screenshot) or Higgsfield `nano_banana_flash` (`higgsfield generate create nano_banana_flash --aspect_ratio 9:16 --image <anchor> --wait --json`).
3. Normalize every shot into `<project_dir>/shots/<shot_id>.png` (`768x1376` RGB PNG):
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/normalize_shot.py "<raw_img>" "<project_dir>/shots/<shot_id>.png"
   ```
4. Build and inspect all 16 shots BEFORE animation or rendering:
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/make_contact_sheet.py "<project_dir>/shots"
   ```
   Call `read_file` on `<project_dir>/shots/contact_sheet.png`. Regenerate any frame with stray text, borders, artifacts, or bright lower-25% clutter.

---

## Phase 3.5 — True Character Animation via Google Flow (`Omni 1.2 Flash`)

Read [omni-flash-animation.md](./references/omni-flash-animation.md) before launching Flow animation:
1. **Budgeting & Cost Guard**: Select **8–11 key action/climax shots** in Hybrid Hero Mode (~3–5 min episodes) or all **6/6** in tight ~60s shorts. **NEVER auto-call Higgsfield `Seedance 2.5` (`seedance_2_5`)** without explicit user approval.
2. **Flow Protocol (`9:16 / 720p / 8s / x1`, `24` credits/clip)**:
   - Pick Start Frames directly from the same Flow `Nano Banana 2.1` project library (use User Upload Handoff only when importing external stills).
   - Send **1 clip per browser batch** using the 4-block formula (Style/Identity Lock + No-Dialogue/Native-Foley Guard + Adult-Safe Hitchcockian Guard + Timed `0-3s / 3-6s / 6-8s` Beats).
   - If a safety false-positive hits, avoid trigger terms (`crouched`, `minor`, etc.), state `"adult male/female ... in their twenties"`, and perform at most 1 safe atmospheric rewrite; stop immediately on CAPTCHAs.
3. **QC Previews & Tier-1 Foley Extraction**:
   - Download each clip to `<project_dir>/shots/<shot_id>_anim.mp4`, generate `480x854 @ 15fps` preview `.gif`s + 4-frame `shots/<shot_id>_flow_qc.png` strips, and inspect every strip via `read_file`.
   - Extract native synced foley and refresh `audio/master_mix.wav` before Phase 4:
     ```bash
     python3 ~/.gemini/config/skills/horror-storybook-video/scripts/extract_flow_audio.py "<project_dir>"
     python3 "<project_dir>/scripts/make_horror_bgm.py"
     ```

---

## Phase 4 — Hybrid Animation / Gentle Line Boil Render & Mobile Encode

Run the renderer (typically 4–8 minutes in background; wait passively without polling):
```bash
python3 ~/.gemini/config/skills/horror-storybook-video/scripts/render_9x16.py "<project_dir>"
```
Automatically detects `<project_dir>/shots/<sid>_anim.mp4` (decodes at `24fps` with native audio stripped `-an` so `audio/master_mix.wav` remains the single mastered audio track, plays **strictly once** with `30fps` sub-frame linear interpolation, tail deceleration + seamless creeping zoom hold on final frame if `span > 1.65× clip_dur` — never replaying an animation twice, while keeping redundant Line Boil off), and falls back cleanly to static PNG + gentle Line Boil (`amp=0.35, wavelength=115.0, hold_frames=6`) on remaining establishing shots. Ensure shot cut boundaries align tightly to spoken cues so visual subjects never linger past their cue. Writes sample-locked `.srt` beside the MP4 and adds bottom-edge lower scrim, night motes, vignette, subtitles, crossfades, and hard `#000000` blackout at `final_blackout_time`.

---

## Phase 5 — Post-Render QA Gate

1. Confirm background Python/`ffmpeg` processes have completely exited (`ps aux | grep -E "ffmpeg|render_9x16" | grep -v grep`) before probing.
2. Run technical QA and extract the 8-frame rendered QA contact sheet:
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/qa_verify.py \
     "<project_dir>/<output_name>.mp4" \
     "<project_dir>/audio/vo_timeline.json" \
     "<project_dir>/final_qa_sheet.png"
   ```
   Enforces: `h264 Main L3.1`, `720x1280`, `yuv420p`, `30/1`, `aac LC 48000Hz 2ch`, `moov` faststart header, `Input Integrated` in `[-15.5, -13.5] LUFS`, and `Input True Peak < -1.0 dBTP`.
3. Call `read_file` on `<project_dir>/final_qa_sheet.png` and verify: centered two-line title with zero tofu glyphs (`□`), legible white-on-navy subtitles inside dark bottom margins, clean FX, and solid black final frame.

---

## Phase 6 — Private Google Drive Mobile Delivery

1. Upload privately using `gdrive` CLI (`Shared: false`; do **NOT** run `mutate share --type anyone` unless the user explicitly asks to make it public):
   ```bash
   gdrive mutate upload "<project_dir>/<output_name>.mp4" --mime-type "video/mp4" --json
   ```
2. Verify sharing state (`Shared: false`) and exact byte size via `gdrive readonly url "<FILE_ID>"` and `gdrive readonly info "<FILE_ID>"`.
3. Reply in Traditional Chinese with the clickable Google Drive mobile link at the top, clickable URL-encoded `file://` links to the MP4, `.srt`, `shots/contact_sheet.png`, and `final_qa_sheet.png`, plus ONLY directly observed metrics. Leave idle browser subagents untouched and never print API keys.
