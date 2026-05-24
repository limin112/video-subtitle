# video-subtitle

给任意视频加**硬字幕**的全流程 [Claude Code](https://claude.com/claude-code) Skill：
**whisper.cpp 本地识别（自带逐句真实时间戳）→ Claude 通读纠错（同音字 / 专有名词）→ 生成 SRT → ffmpeg + libass 烧录**。

字号 / 字体 / 颜色 / 黑底白字 / 描边均可定制，一套脚本复用于不同视频。
也支持把**纯英文 / 外语视频配上「外语原文 + 中文」中外双语字幕**（Claude 逐句翻译，中文在上较大、原文在下较小）。

```
抽音轨 → whisper.cpp 识别 → Claude 纠错 → 生成 SRT → [可选]人工核对 → 烧录(ffmpeg+libass)
```

## 依赖（首次安装，之后复用）

| 组件 | 安装 | 用途 |
|---|---|---|
| whisper.cpp | `brew install whisper-cpp` | 语音识别（Apple Metal 加速），提供 `whisper-cli` |
| ggml 模型 | 下载 `ggml-large-v3-turbo.bin`（~1.6GB）到 `~/.cache/whisper.cpp/` | 识别模型 |
| 带 libass 的 ffmpeg | `brew install ffmpeg-full` | 烧录硬字幕（自带 `ffmpeg` 常无 libass） |

模型下载：
```bash
mkdir -p ~/.cache/whisper.cpp
curl -L --fail -o ~/.cache/whisper.cpp/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

## 脚本

| 脚本 | 作用 |
|---|---|
| `scripts/srt_to_cues.py` | whisper 输出的 SRT → 统一 `cues.json`，可同时应用纠错表并写出纠错后 SRT |
| `scripts/cues_to_srt.py` | `cues.json` → SRT |
| `scripts/srt_to_ass.py` | `cues.json` → ASS（**单语**：字号 / 字体 / 黑底白字或描边 / 分辨率，字号=真实像素） |
| `scripts/bi_ass.py` | 双语 `cues_bi.json` → ASS（**中外双语**：中文在上较大、原文在下较小；box 半透明底框或描边） |
| `scripts/split_long_cues.py` | 双语长句拆短，保证每条中文 ≤1 行（按标点断句、时间按比例切分） |
| `scripts/make_review_html.py` | 交互式核对页：左播视频、右逐条字幕，文字与时间轴可改，导出 SRT |

## 快速用法

```bash
# 1. 抽 16k 单声道音轨
ffmpeg -y -i video.mp4 -ar 16000 -ac 1 -c:a pcm_s16le audio16k.wav

# 2. whisper.cpp 识别 → SRT（真实逐句时间戳）
whisper-cli -m ~/.cache/whisper.cpp/ggml-large-v3-turbo.bin \
  -f audio16k.wav -l zh -osrt -of video_whisper -t 8

# 3. 纠错（通读 video_whisper.srt，写 corrections.txt：错词=>对词）→ cues.json + 纠错后 SRT
python3 scripts/srt_to_cues.py --srt video_whisper.srt --cues cues.json \
  --corrections-file corrections.txt --out-srt video_final.srt

# 4. cues.json → ASS（样式可调）
python3 scripts/srt_to_ass.py --cues cues.json --out video.ass \
  --fontsize 48 --style box --font "Hiragino Sans GB" --res 1920x1080

# 5. 烧录硬字幕
ffmpeg -y -i video.mp4 -vf "ass=video.ass" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart 成片_字幕版.mp4
```

> 烧整段前先抽一帧样片确认字号 / 样式 / 字体：
> `ffmpeg -i video.mp4 -vf "ass=video.ass" -ss 4 -frames:v 1 -y sample.png`

## 双语字幕（外语视频 → 中外双语）

按源语言识别（如 `-l en`），由 Claude 逐句**纠错 + 译成中文**，产出双语 `cues_bi.json`（每条含 `zh` / `en` / `start` / `end`），然后：

```bash
# 先拆长句：保证每条中文在该字号/分辨率下 ≤1 行（参数须与 bi_ass.py 一致）
python3 scripts/split_long_cues.py --in cues_bi.json --out cues_bi_split.json \
  --zh-size 120 --res 2560x1440 --margin-h 40

# 生成双语 ASS（中文在上大、英文在下小；box 半透明底框）
python3 scripts/bi_ass.py --cues cues_bi_split.json --out bi.ass \
  --style box --zh-size 120 --en-size 50 --res 2560x1440 --box-alpha 40 --margin-h 40

# 烧录同上（-vf "ass=bi.ass"）。抽帧确认须用 -copyts 且 -ss 放 -i 前：
ffmpeg -loglevel error -copyts -ss 60 -i video.mp4 -vf "ass=bi.ass" -frames:v 1 -y sample.png
```

完整的 agent 工作流与注意事项见 [`SKILL.md`](SKILL.md)；烧录与识别细节见 [`references/`](references/)。

## 泛化到不同视频

用户只需提供视频（外加可选样式偏好）。`--res` / `--duration` 由 ffprobe 探测；`corrections.txt` 由 Claude 通读该视频转写后自动生成；模型、whisper.cpp、ffmpeg-full 装一次后所有视频复用。非中文改 `whisper-cli -l <code>` 并换对应语言系统字。
