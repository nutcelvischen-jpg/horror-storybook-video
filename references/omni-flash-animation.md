# Google Flow `Omni 1.2 Flash` True-Animation Guide (Hybrid / Full A-Engine)

> Combine **locked dark-storybook Start Frames** (generated in the same Google Flow `Nano Banana 2.1` project) with **Google Flow `Omni 1.2 Flash`** so characters physically walk, tremble, turn their heads, grip railings, and shine trembling flashlights without style drift—while capturing optional frame-synced native horror foley at `0` extra credits.

---

## 1. Engine Selection, Budgeting & Strict Cost Rule

| Production Mode | When to Use | Animated Shots | Est. Flow Credits (`720p / 8s / x1`) |
| :--- | :--- | :--- | :--- |
| **Hybrid Hero Animation (Recommended for ~3–5 min episodes)** | Long multi-act PTT Marvel / horror adaptations (16 shots total) | **6–11 hero shots** (`shots/<sid>_anim.mp4`) covering key character actions & peaks; calm establishing shots stay `shots/<sid>.png` + gentle Line Boil | ~144–264 credits |
| **Full Animation (~60s focused short)** | Tight 6-scene horror shorts (8–10s per scene) | **6 / 6 scenes** animated via `Omni 1.2 Flash` | ~144 credits |

- **Primary Engine Rule**: **Google Flow `Omni 1.2 Flash`** (`9:16 / 720p / 8s / x1`, `24` credits/clip) is **ALWAYS primary**.
- **Strict Cost Guard (Higgsfield Video)**: **NEVER auto-call Higgsfield `Seedance 2.5` (`seedance_2_5`)**—it is far too expensive for routine generation. Only invoke Higgsfield video with explicit user approval if Flow hits a shortfall.

Place finished 720p clips at `<project_dir>/shots/<shot_id>_anim.mp4`. `scripts/render_9x16.py` auto-detects `_anim.mp4` shots and strips native audio during video decode (`-an`).

---

## 2. Flow Configuration Lock

Inside `https://flow.google.com/` project settings:
- **Mode**: `Video` -> `Frames` (`Start` slot only; leave `End` empty unless explicitly doing a 2-keyframe morph)
- **Model**: `Omni 1.2 Flash`
- **Aspect Ratio**: `9:16` (Portrait)
- **Resolution / Duration / Batch**: `720p` / `8s` / `x1` (`24 credits/clip`)

---

## 3. Four-Block Start-Frame Animation Prompt Formula

Always start from an approved `768×1376` normalized illustration (or its same-project Flow `Nano Banana 2.1` original) in the **Start** slot and assemble every prompt from these 4 blocks:

1. **Block 1 — Style & Identity Lock**:
   `Animate this exact European indie dark-storybook charcoal-ink and matte gouache 9:16 illustration without changing the art style, line weight, character face, wardrobe, or architecture.`
2. **Block 2 — Native Flow Synchronized SFX vs. Silent Guard**:
   - **Default for action / prop hero shots (Native Synchronized SFX, `0` extra credits)**:
     `No dialogue, no human speech, no music, no baked subtitles, no bottom text, clean uncluttered lower margin, no watermarks. Sound design: <exact frame-synced diegetic object/horror foley>.`
     *(E.g., heavy corridor footsteps echoing on concrete, heavy iron rolling door grinding open, two loud hollow knocks on a restroom stall door. `Omni 1.2 Flash` embeds frame-synced audio inside `<sid>_anim.mp4`, which `scripts/extract_flow_audio.py` extracts to `audio/flow_sfx/flow_<sid>.wav` and mixes ducked into `audio/master_mix.wav`—while `render_9x16.py` continues decoding video `-an` so LUFS/True Peak mastering stays unified in `master_mix.wav`.)*
   - **Pure drone / silence guard (when total quiet is desired)**:
     `Silent scene, mouths closed, no dialogue, no audible speech, no baked subtitles, no bottom text, clean uncluttered lower margin, no watermarks.`
     *(Prevents `Omni 1.2 Flash` from inventing off-script dialogue or faint lower-edge caption smears during phone/conversation shots.)*
3. **Block 3 — Hitchcockian Safety Guard**:
   Keep threat atmospheric and psychological (empty wooden chair facing away, trembling flashlight beams, flickering porch lamp, mist, back-turned faceless silhouette, abstract red ink strokes—never bodies, nooses, weapons, or gore).
4. **Block 4 — Timed Causal Beats (`0-3s` / `3-6s` / `6-8s`)**:
   Divide the 8 seconds into active physical cause-and-effect beats rather than passive idling:
   - `0-3s [framing]`: ambient motion + anticipation (mist drifting, bulb flickering, character noticing something).
   - `3-6s [camera move + action]`: concrete physical movement (hand gripping rail/table, heavy footsteps climbing stairs, head turning over shoulder toward window/doorway, flashlight beams creeping across wet tile).
   - `6-8s [chilling linger]`: tension hold (bulb flickers off/on, widening dot eyes, shadow deepening at frame exit).

Close with: `Distinct 2D hand-drawn dark-storybook animation, smooth subtle motion, no 3D CGI, no photorealism, no camera cuts.`

---

## 4. Flow Selection, Hygiene & Safety Protocol

1. **Same-Project Start Frame Selection (Primary)**: When stills were generated inside the same Google Flow `Nano Banana 2.1` project, select each `<shot_id>` Start Frame straight from Flow's project library with **zero manual uploads**.
2. **User Upload Handoff (External Stills Only)**: Only when importing external stills (e.g., Gemini Web or Higgsfield fallback), ask the user to multi-select the hero `<shot_id>.png` files from `<project_dir>/shots/` and click **`Upload media`** in Flow's `"Select a frame image"` dialog (browser sandboxes block automated `setInputFiles` on Google-authenticated Flow pages).
3. **Browser Subagent Hygiene & Strictly Sequential Generation**:
   - Send **1 animation clip per browser subagent message** on long sessions so prompts never get truncated during context compaction.
   - Assign Start Frame (verify exact thumbnail visually) -> paste 4-block prompt -> submit -> wait until 100% rendered -> download `720p (Original size)` MP4 to `<project_dir>/shots/<shot_id>_anim.mp4` -> pause ~5 seconds before starting the next clip. Never rapid-fire parallel Flow submissions.
4. **Automated Safety False-Positive Avoidance**:
   - Avoid trigger phrasing such as `"crouched / shaking violently / terrified child / minor"` on stylized young characters.
   - State explicitly `"adult male/female ... in their twenties"` and focus action beats on lighting shifts, shadow drift, mist, camera creep, and object motion.
   - Perform **at most 1 safe atmospheric rewrite** if a policy refusal occurs before stopping and re-scoping.
5. **CAPTCHA / Bot Check Rule**:
   - If Flow shows ANY CAPTCHA, reCAPTCHA challenge, "verify you are human", or "unusual activity" prompt, **STOP immediately**, report to the user so they can verify in the browser pane, and resume in the same Flow tab afterward. Never bypass bot checks.

---

## 5. Audio Mute, Sub-Frame 30fps Blending & Single-Pass Motion Rule

Inside `scripts/render_9x16.py`:
- **Audio Muting**: Decodes `_anim.mp4` with `-an` and switches audio exclusively to `audio/master_mix.wav` (`Algenib` narration + custom horror SFX).
- **Single-Pass Only Rule (Never Replay Twice)**: Every AI character animation plays **strictly once (`0 -> N-1`)**. Replaying a character movement twice (even via mid-shot crossfade) breaks immersion immediately.
- **24fps -> 30fps Linear Sub-Frame Interpolation**: Decodes clips at native `24fps` (`768×1376`) and linearly interpolates intermediate timestamps so slowed playback (`<= 1.65× clip_dur`) remains fluid at `30fps` without stutter.
- **Tail Deceleration + Seamless Creeping Hold (`span > 1.65 × clip_dur`)**: When a shot runs longer than `1.65 × clip_dur` (`~13.3s` for an 8s clip), animation plays once across `[0, play_dur]` with smooth tail deceleration (`1 - (1 - dt/play_dur)^1.35`) so character motion settles gently, then holds seamlessly on the final frame while the lens continues a slow creeping tension zoom across the remaining beat alongside drifting night motes and lighting FX.
- **Cue-Locked Cut Boundaries**: Align visual cut boundaries directly to the exact `vo_timeline.json` cue where each subject enters (e.g., cutting from dog-on-bed directly to stray-cat-at-door on the cat cue midpoint) rather than forcing fixed 2-cue splits.
- **Lower-Edge Scrim Guard**: Applies a deeper bottom `110px` darkening ramp (`y=1170..1280`, up to `alpha=0.92` `#040710`, well below `y=1035` subtitles) to clean up any subtle lower-edge AI compression haze.
