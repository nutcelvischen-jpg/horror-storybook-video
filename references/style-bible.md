# Style Bible, `project.json` Schema & Safe Image Generation Guide

## 1. `project.json` Schema

Place `<project_dir>/project.json` in your episode workspace before running `gen_tts_locked.py` and `render_9x16.py`:

```json
{
  "output_basename": "怪談EPXX_故事標題_9x16",
  "title_main": "《故事主標題》",
  "title_tag": "地點標籤｜副標題懸念",
  "tts": {
    "model": "google/gemini-3.8-flash-tts",
    "voice": "Algenib",
    "fallback_voice": "Enceladus",
    "intra_cue_gap_sec": 0.22,
    "inter_scene_gap_sec": 0.45,
    "final_tail_sec": 1.40,
    "instructions": "Speak in a deeply eerie, low, cold, breathy midnight ghost-storyteller tone with dark brooding intimacy and crisp, steady pacing. Drop quieter and more chilling on whispered quotes or eerie revelations—never cheerful, never theatrical."
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
        { "id": "s01_c1", "slot": "a", "text": "第一句控制十五字內，\n兩行換行剛好置中。" }
      ]
    }
  ]
}
```

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

## 4. Gemini Web Continuous-Chat Capture Protocol

Generating all 16 shots inside **one fresh Gemini Web chat** preserves architecture & wardrobe continuity far better than isolated calls:
1. Navigate to a brand-new chat (`https://gemini.google.com/app`), enable `Tools -> Create image`, set `Aspect ratio: 9:16`.
2. Send prompts in **4 batches of 4** (`s01_a..s02_b`, `s03_a..s04_b`, `s05_a..s06_b`, `s07_a..s08_b`) in that same chat.
3. Resize the browser viewport to `{ width: 801, height: 1011 }` before clicking each thumbnail into its full-screen lightbox and capturing a clean PNG screenshot (larger viewports can clip portrait lightboxes).
4. Normalize every screenshot with `normalize_shot.py`, build `shots/contact_sheet.png`, and inspect every tile via `read_file` before video rendering.
5. **Anti-bot safety rule**: If any web generator shows a CAPTCHA or unusual-activity check, stop automating that origin immediately—never bypass or retry bot checks. Fall back to `image-generator` subagent or another clean path.
