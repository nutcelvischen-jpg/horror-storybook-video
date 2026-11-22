# Style Bible, `project.json` Schema & Safe Image Generation Guide

## 1. `project.json` Schema

Place `<project_dir>/project.json` in your episode workspace before running `gen_tts_locked.py` and `render_9x16.py`:

```json
{
  "output_basename": "怪談EPXX_故事標題_9x16",
  "title_main": "《故事主標題》",
  "title_tag": "地點標籤｜副標題懸念",
  "boil": {
    "amp": 0.35,
    "wavelength": 115.0,
    "hold_frames": 6
  },
  "tts": {
    "model": "google/gemini-3.8-flash-tts",
    "voice": "Algenib",
    "fallback_voice": "Enceladus",
    "intra_cue_gap_sec": 0.22,
    "inter_scene_gap_sec": 0.45,
    "final_tail_sec": 1.40,
    "instructions": "Speak in a deeply eerie, low, cold, breathy midnight ghost-storyteller tone with dark brooding intimacy and crisp, steady pacing. Drop quieter and more chilling on whispered quotes or eerie revelations—never cheerful, never theatrical.",
    "roles": {
      "narrator": {
        "voice": "Algenib",
        "fallback_voice": "Charon",
        "fx": "narrator",
        "instructions": "Deeply eerie, low, cold, breathy midnight ghost-storyteller tone."
      },
      "boss_room": {
        "voice": "Orus",
        "fallback_voice": "Charon",
        "fx": "warehouse_room",
        "instructions": "Warm, grounded slightly older male speaker inside a cavernous room."
      },
      "boss_phone": {
        "voice": "Orus",
        "fallback_voice": "Charon",
        "fx": "phone_rx",
        "instructions": "Friendly-then-alarmed older male speaker heard over a mobile call."
      },
      "protag_casual": {
        "voice": "Enceladus",
        "fallback_voice": "Puck",
        "fx": "warehouse_room",
        "instructions": "Polite young adult male speaker casually replying in an echoey bay."
      },
      "protag_panic": {
        "voice": "Enceladus",
        "fallback_voice": "Kore",
        "fx": "stall_reverb",
        "max_per_char": 0.85,
        "instructions": "Trembling, choked, terrified near-whisper inside a cramped tiled booth."
      },
      "master": {
        "voice": "Gacrux",
        "fallback_voice": "Charon",
        "fx": "temple_reverb",
        "max_per_char": 0.70,
        "instructions": "Grave, solemn older temple elder delivering a measured warning."
      }
    }
  },
  "camera_moves": {
    "s01_a": [1.00, 1.08, 0.00, 0.00, 0.10, -0.10]
  },
  "shot_fx": {
    "s02_a": ["porch_flicker"],
    "s03_a": ["humid_mist"],
    "s04_b": ["police_strobe"],
    "s05_a": ["flashlight_dread"],
    "s05_b": ["crimson_pulse"],
    "s06_b": ["stair_flicker"],
    "s07_b": ["incense_glow"],
    "s08_b": ["closing_vignette"]
  },
  "snappy_cut_shots": ["s08_b"],
  "scenes": [
    {
      "id": "s01",
      "cues": [
        {
          "id": "s01_c1",
          "slot": "a",
          "role": "narrator",
          "text": "第一句控制十五字內，\n兩行換行剛好置中。"
        },
        {
          "id": "s01_c2",
          "slot": "b",
          "role": "protag_panic",
          "instructions": "Optional per-cue voice delivery override for this line only.",
          "text": "「……救我，\n這裡好像有東西。」"
        }
      ]
    }
  ]
}
```

### Multi-Voice `tts.roles` & Gentle `boil` Settings
- **`boil` (Static Shot Line Boil)**: Set `{"amp": 0.35, "wavelength": 115.0, "hold_frames": 6}` for subtle, organic hand-drawn micro-tremor on static PNG shots without harsh jitter.
- **Multi-Voice `tts.roles` (Backward Compatible)**: `tts.roles` and cue-level `"role"` / `"instructions"` are optional—single-voice episodes omitting them fall back cleanly to `tts.voice`, `tts.instructions`, and `"narrator"`.
  - Supported `fx` presets (applied cleanly pre-stitch): `narrator`, `warehouse_room`, `phone_rx` (`320–3300Hz` telephone bandpass + compression), `stall_reverb` (tight tiled booth), `temple_reverb` (solemn hall), and `hall_far` (receding corridor/stairwell).
  - Each role entry also accepts optional `fallback_voice`, `max_per_char` (default `0.48`), `noise_db`, and `min_silence_dur`.

### Supported `shot_fx` Presets
- `porch_flicker`, `stair_flicker`: Erratic tungsten porch/stairwell lamp flicker.
- `humid_mist`: Swelling damp greenish-slate miasma band across mid-frame.
- `police_strobe`: Soft alternating red/blue emergency flash over window glass.
- `flashlight_dread`: Tightening dark tunnel edge + swaying cold flashlight cone.
- `crimson_pulse`: Low-frequency sinister crimson glow pulse in upper half.
- `incense_glow`: Warm flickering temple/candle aura surrounded by heavy shadow.
- `camera_flash`: Crisp 2-frame vintage flash burst at shot midpoint.
- `window_bangs`: Synchronized storm impacts with rapid frame tremor.
- `closing_vignette`: Progressive edge darkening toward final `#000000` blackout.

### Subtitle & Title Guardrails
- Always separate `title_tag` clauses with `｜` (`U+FF5C`) or `·` (`U+00B7`) — **never** `・` (`U+30FB`), which renders as `□` in macOS `Songti TC Bold`.
- Keep every subtitle line `<= 15` Traditional Chinese characters (max 2 lines per cue).
- Never alter spoken words vs displayed subtitles (`cue["text"]` drives both TTS and on-screen burn-in / `.srt` for zero drift).

---

## 2. European Indie Dark-Storybook Prompt Bible

Use this visual anchor sentence in every batch:

> Vertical 9:16 European indie dark-storybook charcoal-ink and matte gouache illustration, deep midnight slate-blue `#0E1726`, weathered concrete/stone greys, sickly tungsten amber `#D99B4E`, faint crimson accents, pale stylized characters with minimalist dot eyes, full-bleed edge-to-edge composition, dark uncluttered lower 25% for clear bottom darkness. Strictly NO readable text, NO Chinese characters, NO English letters, NO numbers, NO license plates, NO borders, NO split panels, NO watermarks.

Before Batch 1, lock 1-line recurring descriptions for:
1. **Architecture**: exact facade, floor count, stair placement, door/utility fixtures.
2. **Primary cast**: hair, glasses, signature coat/cardigan color so outfits stay locked across all 16 shots.

> **Storybook Illustration vs. Photoreal POV Decision Box**
> - **European Dark-Storybook Charcoal-Ink (`#0E1726` / `#D99B4E`) — Default**: Highest automated safety pass rate across image/video filters, strongest 16-shot face & wardrobe continuity via pale stylized faces and minimalist dot eyes, and safest framing for youth, campus, or Taiwanese urban legend adaptations (always describe stylized young characters explicitly as adults in their twenties during animation).
> - **Realistic First-Person POV / Found-Footage — Specialized Only**: Use **only** when zero youth or human-portrait faces appear on camera—frame strictly through POV hands, trembling flashlight beams, doorways, mirrors without clear faces, and physical props so live-action face drift across 16 shots and minor-safety false positives are completely avoided.

---

## 3. Hitchcockian Safety Substitution Table

Never prompt graphic violence, self-harm, corpses, or religious provocation—safety filters block generation and halt pipelines. Use psychological framing instead:

| Narrative Element | Avoid Prompting | Use Instead |
| :--- | :--- | :--- |
| Hanging / Suicide discovery | Body, rope, noose, corpse | Forced-open dark doorway, cold flashlight beams illuminating an **empty wooden chair facing away toward the far dark wall** and dark water reflections on floor tiles |
| Curse notes / Blood messages | Readable Chinese/English curse text, blood spatter | Ragged paper strips marked **only with frantic abstract crimson-red ink brushstrokes and unreadable smears** |
| Sealed / Foreclosed door | Readable court seal characters/dates | Torn diagonal **white-and-red abstract striped paper tape** across the latch |
| Murder / Bloodstain scene | Weapon, wound, gore | Overturned stool, shattered ceramic shard, dark wet trail disappearing into pitch blackness |
| Taboo church / shrine scene | Graphic idol desecration | Empty candlelit dark stone hall, zero crosses, cold ash motes, towering oppressive silhouettes |
| Ghostly pursuer / Doppelganger | Gory monster face | Gaunt faceless silhouette climbing dimly lit exterior stairs from behind, or faint motionless shadow standing inside glass entrance alcove |

---

## 4. Google Flow FIRST Image Generation Protocol (`Nano Banana 2.1`, `9:16`, `1K`, `0` Credits)

Generate all 16 stills inside **one clean Google Flow project** (`https://flow.google.com/` -> `Image` -> `Nano Banana 2.1` -> `9:16` -> `x1`) as the primary workflow:
1. **Why Flow First**: Costs **`0` Flow credits**, outputs clean borderless **`1K` (`Original size`)** PNG/JPG downloads (zero lightbox cropping required), and keeps all 16 stills inside the same Flow project library so Phase 3.5 `Omni 1.2 Flash` animations pick Start Frames directly with **zero manual uploads**.
2. **Browser Hygiene Rule**: Send **at most 2 shot prompts per browser subagent message** (e.g., `s01_a` + `s01_b`) so long visual prompts never suffer subagent context-compaction truncation.
3. **Normalize & Inspect Gate**: Normalize every downloaded image via `normalize_shot.py` (`768×1376` RGB PNG), build `shots/contact_sheet.png` via `make_contact_sheet.py`, and inspect every tile via `read_file` before animating or rendering (regenerate any shot showing stray text, numbers, borders, or bright lower-25% clutter).
4. **Fallback Engines (Use ONLY when Flow hits quota/limits)**:
   - **Gemini Web Fallback**: Open one fresh chat (`https://gemini.google.com/app`, `Tools -> Create image`, `Aspect ratio: 9:16`), send 4 batches of 4 (`s01_a..s02_b`, ..., `s07_a..s08_b`), resize browser viewport to `{ width: 801, height: 1011 }`, and screenshot each full-screen lightbox cleanly.
   - **Higgsfield `nano_banana_flash` Fallback**: First generate anchor shots (`s02_a`, `s02_b`, `s04_b`), then pass `--image <anchor_path>` for style/cast continuity:
     ```bash
     higgsfield generate create nano_banana_flash --aspect_ratio 9:16 --image "<anchor_path>" --prompt "<shot_prompt>" --wait --json
     ```
5. **Anti-Bot Safety Rule**: If any web generator shows a CAPTCHA, reCAPTCHA, or unusual-activity check, stop automating that origin immediately—never bypass or retry bot checks. Ask the user to verify in the browser pane or switch cleanly to a permitted fallback above.
