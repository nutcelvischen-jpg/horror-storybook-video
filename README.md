# horror-storybook-video

> 9:16 歐洲暗黑繪本風恐怖短片導演 Skill：結合 **Google Flow (`Nano Banana 2.1`) 零點數連貫分鏡**、**Google Flow `Omni 1.2 Flash` 單次角色真動畫與原生同步音效**、**多聲線逐句鎖定零漂移配音**、**三層恐怖音場設計** 與 **跨手機播放相容編碼及私人 Google Drive 交付**。
>
> An end-to-end Agent Skill for producing mobile-ready 9:16 European indie dark-storybook horror shorts combining **Flow-first `Nano Banana 2.1` continuous stills**, **Google Flow `Omni 1.2 Flash` single-pass character animation + native synced foley**, **multi-voice sample-locked narration & subtitles**, **3-tier spatial horror sound design**, and **automated mobile QA**.

---

## 核心特色 / Key Capabilities

1. **Google Flow 優先連貫分鏡＋單次播放真動畫（Flow-First Stills & Single-Pass `Omni 1.2 Flash`）**
   - 先於單一 **Google Flow** 專案使用 `Nano Banana 2.1`（`9:16 / 1K / x1`，`0` 點數，每批最多 2 鏡）產出無邊框暗黑繪本分鏡（含希區考克式安全替代與成年角色語意，並以 Gemini Web / Higgsfield `nano_banana_flash` 作為額度備援）。
   - 直接於同一 Flow 專案選取起始幀送入 **`Omni 1.2 Flash` (`9:16 / 720p / 8s / x1`)**，以 4 段式分時動作提示詞生出 `24fps` 真動畫（`shots/<sid>_anim.mp4`），並產出 `480x854 @ 15fps` 預覽 `.gif` 與 4 幀 `*_flow_qc.png` 條帶供人工目檢。嚴禁未經明確同意自動呼叫高價的 Higgsfield `Seedance 2.5`。
   - 渲染器 [`render_9x16.py`](./scripts/render_9x16.py) 自動偵測 `_anim.mp4`，解碼時抽離原聲（`-an`）以確保單一母帶混音，並**嚴格單次播放**（`24fps -> 30fps` 亞幀線性內插，長鏡尾段自動平滑減速定格微推，絕不重播兩次）；其餘鋪陳鏡頭無縫回退至溫和的 4 幀手繪微顫（`amp=0.35, wavelength=115.0, hold_frames=6`）＋飄浮微粒。
2. **多聲線逐句獨立配音與 `0.0000s` 零漂移字幕鎖定**
   - [`gen_tts_locked.py`](./scripts/gen_tts_locked.py) 支援 `tts.roles` 多角色分軌（例如旁白 `Algenib`、主管 `Orus`、主角 `Enceladus`、師父 `Gacrux`）與內建 6 種預混音空間濾鏡（`narrator`、`warehouse_room`、`phone_rx`、`stall_reverb`、`temple_reverb`、`hall_far`），同時完全相容舊版單一聲線 `project.json`。
   - 強制 **口播文字與畫面字幕 1:1 完全一致**，自動查驗 `Songti TC Bold` 與 `Heiti TC Medium` 缺字方框（`.notdef` tofu mask）及 `<= 600px` 寬度，精確寫入 `audio/vo_full.wav` 與 `audio/vo_timeline.json`。
3. **三層恐怖音效架構＋AAC 峰值防破音**
   - **Tier 1（Flow 原生同步音效，`0` 額外點數）**：由 [`extract_flow_audio.py`](./scripts/extract_flow_audio.py) 自 `shots/*_anim.mp4` 抽取 `48kHz` 立體聲擬真音效（`audio/flow_sfx/`）並寫入 `flow_audio_manifest.json`，再回饋混入 `audio/master_mix.wav`。
   - **Tier 2（Higgsfield `seed_audio` 靜態鏡頭補位）**：遇 Cloudflare 驗證擋爬之網站絕不繞過，僅於靜態鏡音效缺口時以 `@higgsfield/cli` 呼叫 `seed_audio` 補足。
   - **Tier 3（Python/FFmpeg 程式化音場）**：依據 [horror-sfx-recipes.md](./references/horror-sfx-recipes.md) 建構低頻不協和 Drone、2 秒真空驟停與 `-13 dB` 倒帶混響鬼語，並於混音尾端串接 `loudnorm=I=-14.0:TP=-2.0:LRA=10,alimiter=limit=0.6310` 確保首次渲染即達標。
4. **跨手機相容編碼與自動品檢（QA Gate）**
   - 統一封裝為 `H.264 Main Profile Level 3.1`、`720x1280 @ 30fps`、`yuv420p`、`AAC-LC 48kHz 2ch`、`+faststart`；[`qa_verify.py`](./scripts/qa_verify.py) 自動查驗串流規格、`-15.5 ~ -13.5 LUFS`、`< -1.0 dBTP` 並輸出 8 幀抽樣檢查表。

---

## 工作流程 / 7-Phase Pipeline

| Phase | Stage | Output |
| :--- | :--- | :--- |
| **Phase 0** | 多頁怪談爬蟲整理與結局提案確認 | Verified chronological beat sheet |
| **Phase 1** | 撰寫 `project.json` 與多聲線／單聲線逐句鎖定 TTS 合成 | `audio/vo_full.wav`, `audio/vo_timeline.json` |
| **Phase 2** | 三層恐怖音場架構（`seed_audio` 靜態補位＋程式化音場＋預混音限幅） | `audio/master_mix.wav` |
| **Phase 3** | Google Flow `Nano Banana 2.1` 連貫分鏡（Gemini Web / `nano_banana_flash` 備援）＋`contact_sheet` 檢視 | `shots/s01_a.png` .. `shots/s08_b.png` |
| **Phase 3.5** | Google Flow `Omni 1.2 Flash` 關鍵鏡頭真動畫＋`.gif`/`_flow_qc.png` 品檢＋`extract_flow_audio.py` 抽取原生音效回饋混音 | `shots/<sid>_anim.mp4`, `audio/flow_sfx/*`, updated `master_mix.wav` |
| **Phase 4** | 單次真動畫／溫和 Line Boil 9:16 合成壓字與 `+faststart` 封裝 | `<output_basename>.mp4` & `.srt` |
| **Phase 5–6** | `qa_verify.py` 技術視覺驗收 ＋ Google Drive 私密交付（`Shared: false`） | `final_qa_sheet.png` + Drive link |

---

## 安裝方式 / Installation

將本 repo 複製到你的 Agent Skills 目錄：

```bash
# Antigravity / Gemini config skills
git clone https://github.com/nutcelvischen-jpg/horror-storybook-video.git ~/.gemini/config/skills/horror-storybook-video

# Claude Code skills (optional)
git clone https://github.com/nutcelvischen-jpg/horror-storybook-video.git ~/.claude/skills/horror-storybook-video
```

---

## 環境需求 / Prerequisites

- **Python** `>= 3.10`
- **FFmpeg & FFprobe**（需可執行 `libx264`、`aac`、`loudnorm`、`alimiter`）
- **Python 套件**：
  ```bash
  pip install numpy pillow requests soundfile
  ```
- **API / 帳號與工具需求**：
  - `OPENROUTER_API_KEY`（環境變數或傳入 `--key-file`，供 `gen_tts_locked.py` 呼叫 `google/gemini-3.8-flash-tts`）
  - 登入瀏覽器之 **Google Flow**（`Nano Banana 2.1` 首選分鏡與 `Omni 1.2 Flash` 真動畫；Gemini Web 作為分鏡備援）
  - `@higgsfield/cli`（選用，`npm i -g @higgsfield/cli`；用於 Phase 2 靜態鏡頭 `seed_audio` 音效補位或經明確授權之備援；安裝後執行 `higgsfield auth login` 與 `higgsfield workspace set <id>`）
  - `gdrive` CLI（選用，用於 Phase 6 私人 Google Drive 交付）
- **字體（macOS 預設路徑）**：
  - 片頭字體：`/System/Library/Fonts/Supplemental/Songti.ttc`（index `2`, `Songti TC Bold`）
  - 字幕字體：`/System/Library/Fonts/STHeiti Medium.ttc`（index `0`, `Heiti TC Medium`）
  - 若於 Linux/Windows 執行，請修改 `gen_tts_locked.py` 與 `render_9x16.py` 內的字體路徑。

---

## 檔案結構 / Repository Structure

```text
horror-storybook-video/
├── SKILL.md                               # 主工作流規範（Phase 0 ~ Phase 6）
├── README.md                              # 雙語說明文件與安裝指南
├── LICENSE                                # MIT License
├── .gitignore
├── references/
│   ├── style-bible.md                     # project.json 多聲線規範、Flow 首選繪本聖經與安全替代對照表
│   ├── horror-sfx-recipes.md              # 三層恐怖音場架構（Flow 原生/seed_audio/程式化）與混音食譜
│   └── omni-flash-animation.md            # Google Flow Omni 1.2 Flash 四段式動畫、原生音效與單次混剪規範
└── scripts/
    ├── gen_tts_locked.py                  # 多/單聲線逐句 TTS 合成、空間預設濾鏡、字形檢查與 0 漂移時間軸輸出
    ├── extract_flow_audio.py              # 自 *_anim.mp4 抽取 Flow 原生 48kHz 立體聲同步音效與音量清單
    ├── normalize_shot.py                  # 自動去白邊、9:16 裁切並縮放為 768x1376 PNG
    ├── make_contact_sheet.py              # 產出 4x4 16 鏡總覽圖供人工目檢
    ├── make_subtle_gif.py                 # 單鏡 Flow/靜圖循環轉 GIF/_loop.mp4 工具
    ├── render_9x16.py                     # 核心 9:16 合成器（單次 _anim.mp4 與溫和 Line Boil 混剪）
    └── qa_verify.py                       # ffprobe + faststart + LUFS/dBTP + 8 幀視覺抽檢表
```
