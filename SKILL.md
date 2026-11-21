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

## Phase 1 — Project Config & Sample-Locked Per-Cue TTS

1. Initialize workspace `<project_dir>/{shots,audio/cues,scripts}`.
2. Author `<project_dir>/project.json` following the schema in [style-bible.md](./references/style-bible.md):
   - Every cue line `<= 15` CJK characters; 2 lines max per cue.
   - 1:1 literal parity between spoken narration and on-screen subtitle text.
   - **Never** use `・` (`U+30FB`) in `title_tag` (`Songti TC Bold` lacks it and renders `□`); use `｜` (`U+FF5C`) or `·` (`U+00B7`).
3. Run per-cue narration synthesis (`OPENROUTER_API_KEY` env var or `--key-file`, never log or print keys):
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/gen_tts_locked.py "<project_dir>"
   ```
   - Automatically checks `Songti TC Bold` & `Heiti TC Medium` glyphs against the font's `.notdef` tofu mask (`\uffff`) and enforces line width `<= 600px`.
   - Synthesizes each cue individually (`google/gemini-3.8-flash-tts`, voice `Algenib`), trims only leading/trailing silence (`areverse`), auto-retries speed/silence outliers up to 3 attempts, stitches exact sample-locked `audio/vo_full.wav` (reverb tail clamped via `-t`), and writes `audio/vo_timeline.json`.

---

## Phase 2 — Custom Horror Soundscape & Pre-AAC Limiter

1. Read [horror-sfx-recipes.md](./references/horror-sfx-recipes.md) and write `<project_dir>/scripts/make_horror_bgm.py` reading `audio/vo_timeline.json` and `audio/vo_full.wav`.
2. Layer story-specific dread: dissonant sub-drones, regional ambience, a sudden `1.8s–2.2s` total ambient vacuum drop before the core scare, `-13 dB` reverse-reverb ghostly whisper shadows under eerie quotes, causal SFX locked to cue timestamps, and a final door slam / bell cut to silence at `final_blackout_time`.
3. End the ffmpeg master `amix` filter chain with `loudnorm=I=-14.5:TP=-1.5:LRA=10,alimiter=limit=0.7079:attack=5:release=50:level=false:latency=true` so AAC inter-sample overshoot still stays `< -1.0 dBTP` on the first render.
4. Run `make_horror_bgm.py` and verify `audio/master_mix.wav` duration matches `vo_full.wav`.

---

## Phase 3 — 9:16 Illustrations & Contact Sheet Gate

1. Read [style-bible.md](./references/style-bible.md) for consistent architecture/cast prompts and Hitchcockian psychological-horror substitutions (strictly zero readable text, zero borders/split panels, zero corpses/nooses/gore, dark uncluttered lower 25%).
2. Generate all 16 shots in **4 batches of 4** inside ONE continuous fresh Gemini Web chat (`https://gemini.google.com/app`, `Tools -> Create image`, `Aspect ratio: 9:16`), resizing lightbox captures to `{ width: 801, height: 1011 }` before screenshotting (or use `image-generator` when Gemini Web is unavailable; **never** bypass CAPTCHAs or bot checks).
3. Normalize every shot into `<project_dir>/shots/<shot_id>.png` (`768x1376` RGB PNG):
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/normalize_shot.py "<raw_img>" "<project_dir>/shots/<shot_id>.png"
   ```
4. Build and inspect all 16 shots BEFORE animation or video rendering:
   ```bash
   python3 ~/.gemini/config/skills/horror-storybook-video/scripts/make_contact_sheet.py "<project_dir>/shots"
   ```
   Call `read_file` on `<project_dir>/shots/contact_sheet.png`. Regenerate any frame with stray text, borders, visual artifacts, or bright lower-25% clutter.

---

## Phase 3.5 — True Character Animation via Google Flow (`Omni 1.2 Flash`)

Read [omni-flash-animation.md](./references/omni-flash-animation.md) before launching Flow animation:
1. **Budgeting**:
   - **Hybrid Hero Mode (~3–5 min episodes)**: Select **8–11 key action/climax shots** spanning all story acts (leave calm establishing scenes as static PNG + Line Boil).
   - **Full Animation (~60s tight shorts)**: Animate all **6 / 6 scenes**.
2. **User Upload Handoff**: Since automated browser uploads are blocked on Google-authenticated Flow pages, list the exact `<shot_id>.png` files for the user to multi-select via **`Upload media`** into the Flow project's **Uploads** library (`Video -> Frames -> Start -> Omni 1.2 Flash -> 9:16 -> 720p -> 8s -> x1`, `24 credits/clip`).
3. **Sequential 1-by-1 Generation**: Using the 4-block prompt formula (Style/Identity Lock + Silent/No-Subtitles Guard + Hitchcockian Safety Guard + Timed `0-3s / 3-6s / 6-8s` Causal Beats), generate and download **1 clip at a time** (pausing ~5s between clips) to `<project_dir>/shots/<shot_id>_anim.mp4`. If any CAPTCHA/bot check appears, stop immediately and ask the user to verify in the browser pane.

---

## Phase 4 — Hybrid Animation / Line Boil Render & Mobile Encode

Run the renderer (typically 4–8 minutes in background; wait passively for completion without polling):
```bash
python3 ~/.gemini/config/skills/horror-storybook-video/scripts/render_9x16.py "<project_dir>"
```
Automatically detects `<project_dir>/shots/<sid>_anim.mp4` (decodes at `24fps` with native audio stripped `-an`, applies `30fps` sub-frame linear interpolation, smooth beat-2 punch-in crossfade for shots `> 1.45×` clip length, and bypasses redundant Line Boil/heavy pan), while falling back cleanly to static PNG + subtle Line Boil on remaining establishing shots. Writes sample-locked `.srt` beside the MP4 and adds bottom-edge lower scrim, night motes, vignette, subtitles, crossfades, and hard `#000000` blackout at `final_blackout_time`.

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

1. Upload privately using `gdrive` CLI (do **NOT** run `mutate share --type anyone` unless the user explicitly asks to make it public):
   ```bash
   gdrive mutate upload "<project_dir>/<output_name>.mp4" --mime-type "video/mp4" --json
   ```
2. Verify sharing state (`Shared: false`) and byte size via `gdrive readonly url "<FILE_ID>"` and `gdrive readonly info "<FILE_ID>"`.
3. Reply in Traditional Chinese with the clickable Google Drive mobile link at the top, clickable URL-encoded `file://` links to the MP4, `.srt`, `shots/contact_sheet.png`, and `final_qa_sheet.png`, plus ONLY directly observed metrics. Leave idle browser subagents untouched and never print API keys.
