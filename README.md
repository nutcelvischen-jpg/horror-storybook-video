# horror-storybook-video

> 9:16 歐洲暗黑繪本風恐怖短片導演 Skill：結合 **Gemini Web 連貫分鏡插畫**、**Google Flow `Omni 1.2 Flash` 角色真動畫**、**逐句鎖定零漂移字幕配音**、**空間恐怖音效** 與 **跨手機播放相容編碼及私人 Google Drive 交付**。
>
> An end-to-end Agent Skill for producing mobile-ready 9:16 European indie dark-storybook horror shorts combining **Gemini Web continuous-chat illustrations**, **Google Flow `Omni 1.2 Flash` true character animation**, **sample-locked per-cue narration & subtitles**, **spatial horror sound design**, and **automated mobile QA**.

---

## 核心特色 / Key Capabilities

1. **雙引擎混合真動畫（Hybrid A-Engine + Line Boil Fallback）**
   - 先於單一連續 **Gemini Web** 對話中產出畫風、建築與角色服裝完全一致的 `9:16` 暗黑繪本分鏡（含希區考克式安全替代指南，避開血腥與文字）。
   - 將關鍵高潮鏡頭送入 **Google Flow (`Omni 1.2 Flash`, `9:16 / 720p / 8s / x1`)**，以 4 段式分時動作提示詞（風格鎖定 + 靜音無字保護 + 安全語意 + `0-3s / 3-6s / 6-8s` 因果節拍）生出真正會走路、驚恐轉頭、扶梯攀爬與手電筒晃動的 `24fps` 真動畫（`shots/<sid>_anim.mp4`）。
   - 渲染器 [`render_9x16.py`](./scripts/render_9x16.py) 會自動偵測 `_anim.mp4`，抽離原聲後以 `24fps -> 30fps` 亞幀線性內插流暢輸出，長鏡頭自動平滑兩段推進轉場（無生硬跳接），其餘鋪陳鏡頭無縫回退至 4 幀手繪微顫（Line Boil）＋飄浮微粒。
2. **逐句獨立配音與 `0.0000s` 零漂移字幕鎖定**
   - [`gen_tts_locked.py`](./scripts/gen_tts_locked.py) 逐句呼叫 `google/gemini-3.8-flash-tts`（`Algenib` 深夜故事聲線），強制 **口播文字與畫面字幕 1:1 完全一致**，修剪頭尾空白並自動重試語速／異常靜音離群句，以精確取樣點寫入 `audio/vo_full.wav` 與 `audio/vo_timeline.json`。
   - 渲染前自動檢查 `Songti TC Bold` 與 `Heiti TC Medium` 是否存在缺字方框（`.notdef` tofu mask），杜絕片頭／字幕出現 `□`。
3. **空間恐怖音場＋AAC 峰值防破音**
   - 依據 [horror-sfx-recipes.md](./references/horror-sfx-recipes.md) 撰寫劇本專屬低頻不協和 Drone、2 秒真空驟停、`-13 dB` 倒帶混響鬼語與時間軸觸發音效，並在混音尾端串接 `alimiter` 預留 AAC 過採樣餘裕。
4. **跨手機相容編碼與自動品檢（QA Gate）**
   - 統一封裝為 `H.264 Main Profile Level 3.1`、`720x1280 @ 30fps`、`yuv420p`、`AAC-LC 48kHz 2ch`、`+faststart`（`moov` 前置）；[`qa_verify.py`](./scripts/qa_verify.py) 自動查驗串流規格、`-15.5 ~ -13.5 LUFS`、`< -1.0 dBTP` 並輸出 8 幀抽樣檢查表。

---

## 工作流程 / 7-Phase Pipeline

| Phase | Stage | Output |
| :--- | :--- | :--- |
| **Phase 0** | 多頁怪談爬蟲整理與結局提案確認 | Verified chronological beat sheet |
| **Phase 1** | 撰寫 `project.json` 與逐句鎖定 TTS 合成 | `audio/vo_full.wav`, `audio/vo_timeline.json` |
| **Phase 2** | 客製空間恐怖配樂＋音效混音 | `audio/master_mix.wav` |
| **Phase 3** | Gemini Web 連貫分鏡插畫＋`contact_sheet` 檢視 | `shots/s01_a.png` .. `shots/s08_b.png` |
| **Phase 3.5** | Google Flow `Omni 1.2 Flash` 關鍵鏡頭真動畫 | `shots/<sid>_anim.mp4` |
| **Phase 4** | 混剪／微顫 9:16 合成壓字與 `+faststart` 封裝 | `<output_basename>.mp4` & `.srt` |
| **Phase 5–6** | `qa_verify.py` 技術視覺驗收 ＋ Google Drive 私密交付 | `final_qa_sheet.png` + Drive link |

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
- **API / 帳號需求**：
  - `OPENROUTER_API_KEY`（環境變數或傳入 `--key-file`，供 `gen_tts_locked.py` 呼叫 `google/gemini-3.8-flash-tts`）
  - 登入瀏覽器之 Gemini Web 與 Google Flow（`Omni 1.2 Flash` 真動畫生成用）
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
│   ├── style-bible.md                     # project.json 規範、歐洲暗黑繪本提示詞聖經、安全替代對照表
│   ├── horror-sfx-recipes.md              # 恐怖音場與 NumPy/FFmpeg 音效設計食譜
│   └── omni-flash-animation.md            # Google Flow Omni 1.2 Flash 四段式動畫與混剪規範
└── scripts/
    ├── gen_tts_locked.py                  # 逐句 TTS 合成、字形檢查與 0 漂移時間軸輸出
    ├── normalize_shot.py                  # 自動去白邊、9:16 裁切並縮放為 768x1376 PNG
    ├── make_contact_sheet.py              # 產出 4x4 16 鏡總覽圖供人工目檢
    ├── make_subtle_gif.py                 # 單鏡 Flow/靜圖循環轉 GIF/_loop.mp4 工具
    ├── render_9x16.py                     # 核心 9:16 合成器（支援 _anim.mp4 與 Line Boil 混剪）
    └── qa_verify.py                       # ffprobe + faststart + LUFS/dBTP + 8 幀視覺抽檢表
```
