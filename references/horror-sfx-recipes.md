# Horror Soundscape & Pre-AAC Limiter Recipes

Write a project-local `<project_dir>/scripts/make_horror_bgm.py` modeled on these patterns, reading `audio/vo_timeline.json` and `audio/vo_full.wav` so every scare lands on the exact cue sample.

---

## 1. Dissonant Drone Bed + Regional Night Ambience

- **Sub/Tritone Cluster**: Layer sub-octave root + minor second + tritone sine waves with tiny slow stereo detuning (`1.003x` right channel, `±0.2%` pitch drift LFO):
  - Gothic European dread: `C1 / C2 / F#2 / G2` (`midi_to_hz(24, 36, 42, 43)`)
  - Oppressive East Asian apartment/urban dread: `D1 / D2 / Eb2 / Ab2` (`midi_to_hz(26, 38, 39, 44)`)
- **Regional Night Air / Insects**: Slow-modulated filtered Gaussian noise (`-34 dBFS`), plus faint early-act cicada/night shimmer (`s01–s03`) that **vanishes completely** once the horror turns real (`s05+`).
- **Clinical / Stairwell 60Hz Hum**: Subtle `60Hz + 120Hz` fluorescent buzz (`amp=0.020`) during hallway/hospital/staircase acts.
- **Pre-Blackout Swell**: Power-curve (`progress ** 1.5`) dissonant high cluster building across the closing scene straight into `final_blackout_time`, then hard-cut to silence (`15ms` zero-click ramp).

---

## 2. Signature Causal Horror SFX Blocks

Lock timestamps dynamically to `timeline["scenes"][sid]["cues"][k]["start"]`:

### Instant Total Ambient Vacuum Drop (`1.8s–2.2s`)
Multiply the entire ambient/drone `bed` to `0.0` (with `30–40ms` ramps to avoid clicks) right when a character discovers silence outside a raging room or opens a death-scented door:
```python
iva, ivb = int(vac_start * SR), int(vac_end * SR)
fn = int(0.03 * SR)
bed[iva : iva + fn] *= np.linspace(1.0, 0.0, fn)[:, None]
bed[iva + fn : ivb - fn] = 0.0
bed[ivb - fn : ivb] *= np.linspace(0.0, 1.0, fn)[:, None]
```

### `-13 dB` Reverse-Reverb Ghostly Whisper Shadow
Generate a spectral echo that breathes *backward* into terrifying quoted lines or apparitions:
```python
seg = vo_data[i0:i1].mean(axis=1)
rev = seg[::-1]
rev_wet = np.zeros_like(rev)
for d_s, g in [(0.05, 0.44), (0.11, 0.34), (0.19, 0.25), (0.31, 0.17), (0.45, 0.10)]:
    d = int(d_s * SR)
    if d < len(rev):
        rev_wet[d:] += rev[:-d] * g
whisper = rev_wet[::-1]  # lowpass filter + RMS match to -13 dB below VO, pan slightly L/R by 20ms
```

### Compact Synthetic Foley Palette (Zero External Assets Needed)
- **Door Knocks / Prison/Apartment Doors**: Fast downward pitch-swept thud (`145Hz -> 0` over `18ms`) + short filtered noise burst across stereo echoes.
- **Rusted Iron Stair Creak / Door Hinges**: AM pulse-train (`10–17Hz` stick-slip `sin**4`) multiplying harmonic wood/metal formants (`195/330/540Hz`).
- **Metal Door Slam + Temple/Cathedral Bell**: Bronze inharmonic partials (`1.0, 1.19/1.49, 2.02, 3.12`) decaying `1.8s–4.5s` cut sharply at `blackout_t + 0.08s`.
- **Distant Police Beacon / Subway / Lock Prying**: Slow LFO sine siren (`740 ± 190Hz` at `0.9Hz`), 1-pole IIR tunnel rumble + braking screech (`2450 - 380*t`), or metallic screwdriver transient bursts (`2150Hz / 3420Hz`).

---

## 3. Pre-AAC Mastering Chain (Prevents True Peak Overshoot)

Lossy `AAC-LC 192kbps` encoding adds `~0.6 to +1.0 dB` of inter-sample peak overshoot over PCM masters normalized to `-1.5 dBTP`. Always cap the final PCM mix at `-3.0 dBFS` (`limit=0.7079`) with latency compensation **after** `loudnorm`:

```python
filter_complex = (
    "[1:a]volume=0.88[bgm];"
    "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,"
    "loudnorm=I=-14.5:TP=-1.5:LRA=10,"
    "alimiter=limit=0.7079:attack=5:release=50:level=false:latency=true[out]"
)
```

Typical measured result on final encoded MP4:
- **PCM `master_mix.wav`**: `~ -14.8 LUFS`, `~ -3.0 dBTP`
- **Final AAC MP4**: `~ -14.9 LUFS`, `~ -2.5 dBTP` (cleanly passes `[-15.5, -13.5] LUFS` & `< -1.0 dBTP` on first render).
