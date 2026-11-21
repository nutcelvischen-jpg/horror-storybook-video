# Google Flow `Omni 1.2 Flash` True-Animation Guide (Hybrid / Full A-Engine)

> Combine **locked dark-storybook Start Frames** (generated in a continuous Gemini Web chat) with **Google Flow `Omni 1.2 Flash`** so characters physically walk, tremble, turn their heads, grip railings, and shine trembling flashlights without style drift.

---

## 1. Engine Selection & Shot Budgeting

| Production Mode | When to Use | Animated Shots | Est. Flow Credits (`720p / 8s / x1`) |
| :--- | :--- | :--- | :--- |
| **Hybrid Hero Animation (Recommended for ~3–5 min episodes)** | Long multi-act PTT Marvel / horror adaptations (16 shots total) | **8–11 hero shots** (`shots/<sid>_anim.mp4`) covering key character actions & peaks; calm establishing shots stay `shots/<sid>.png` + subtle Line Boil | ~192–264 credits |
| **Full Animation (~60s focused short)** | Tight 6-scene horror shorts (8–10s per scene) | **6 / 6 scenes** animated via `Omni 1.2 Flash` | ~144 credits |

Place finished 720p clips at `<project_dir>/shots/<shot_id>_anim.mp4`. `scripts/render_9x16.py` auto-detects `_anim.mp4` shots and strips native audio.

---

## 2. Flow Configuration Lock

Inside `https://flow.google.com/` project settings:
- **Mode**: `Video` -> `Frames` (`Start` slot only; leave `End` empty unless explicitly doing a 2-keyframe morph)
- **Model**: `Omni 1.2 Flash`
- **Aspect Ratio**: `9:16` (Portrait)
- **Resolution / Duration / Batch**: `720p` / `8s` / `x1` (`24 credits/clip`)

---

## 3. Four-Block Start-Frame Animation Prompt Formula

Always start from an approved `768×1376` normalized illustration in the **Start** slot and assemble every prompt from these 4 blocks:

1. **Block 1 — Style & Identity Lock**:
   `Animate this exact European indie dark-storybook charcoal-ink and matte gouache 9:16 illustration without changing the art style, line weight, character face, wardrobe, or architecture.`
2. **Block 2 — Silent Video & Subtitle Guard**:
   `Silent scene, mouths closed, no dialogue, no audible speech, no baked subtitles, no bottom text, clean uncluttered lower margin, no watermarks.`
   *(Prevents `Omni 1.2 Flash` from inventing off-script Chinese dialogue or faint lower-edge caption smears during phone/conversation shots.)*
3. **Block 3 — Hitchcockian Safety Guard**:
   Keep threat atmospheric and psychological (empty wooden chair facing away, trembling flashlight beams, flickering porch lamp, mist, back-turned faceless silhouette, abstract red ink strokes—never bodies, nooses, weapons, or gore).
4. **Block 4 — Timed Causal Beats (`0-3s` / `3-6s` / `6-8s`)**:
   Divide the 8 seconds into active physical cause-and-effect beats rather than passive idling:
   - `0-3s [framing]`: ambient motion + anticipation (mist drifting, bulb flickering, character noticing something).
   - `3-6s [camera move + action]`: concrete physical movement (hand gripping rail/table, heavy footsteps climbing stairs, head turning over shoulder toward window/doorway, flashlight beams creeping across wet tile).
   - `6-8s [chilling linger]`: tension hold (bulb flickers off/on, widening dot eyes, shadow deepening at frame exit).

Close with: `Distinct 2D hand-drawn dark-storybook animation, smooth subtle motion, no 3D CGI, no photorealism, no camera cuts.`

---

## 4. Flow Upload & Anti-CAPTCHA Protocol

1. **User Upload Handoff**: Browser sandboxes block `setInputFiles` on Google-authenticated Flow pages (`NAVIGATION_NEEDS_PERMISSION`). Ask the user to multi-select all hero `<shot_id>.png` files from `<project_dir>/shots/` and click **`Upload media`** in Flow's `"Select a frame image"` dialog so they reside in the project's **Uploads** gallery.
2. **Strictly Sequential Generation (1 Clip at a Time)**:
   - Assign Start Frame (verify exact thumbnail visually) -> paste 4-block prompt -> submit -> wait until 100% rendered -> download `720p (Original size)` MP4 to `browser_sandbox/downloads/` -> pause ~5 seconds before starting the next clip.
   - Never rapid-fire parallel Flow submissions (triggers reCAPTCHA rate limits).
3. **CAPTCHA / Bot Check Rule**:
   - If Flow shows ANY CAPTCHA, reCAPTCHA challenge, "verify you are human", or "unusual activity" prompt, **STOP immediately**, report to the user so they can verify in the browser pane, and resume in the same Flow tab afterward. Never bypass bot checks.

---

## 5. Audio Mute, Sub-Frame 30fps Blending & Long-Shot Beat Extension

Inside `scripts/render_9x16.py`:
- **Audio Muting**: Decodes `_anim.mp4` with `-an` and switches audio exclusively to `audio/master_mix.wav` (`Algenib` narration + custom horror SFX).
- **24fps -> 30fps Linear Sub-Frame Interpolation**: Decodes clips at native `24fps` (`768×1376`) and linearly interpolates intermediate timestamps so `0.75x–0.85x` atmospheric slow-downs remain fluid at `30fps` without stutter.
- **Smooth 2-Beat Punch-In (`span > 1.45 × clip_dur`)**: Shots exceeding ~11.6s smoothly play Beat 1 (`0..clip_dur`, `1.00 -> 1.03` zoom) across the first half and crossfade smoothly (`±0.40s` `smoothstep` around midpoint) into Beat 2 with closer dramatic framing (`1.05 -> 1.09` zoom), avoiding harsh loop snaps.
- **Lower-Edge Scrim Guard**: Applies a deeper bottom `110px` darkening ramp (`y=1170..1280`, up to `alpha=0.92` `#040710`, well below `y=1035` subtitles) to clean up any subtle lower-edge AI compression haze.
