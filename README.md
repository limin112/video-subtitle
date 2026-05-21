# video-subtitle

给任意视频加**硬字幕**的全流程 [Claude Code](https://claude.com/claude-code) Skill：
**whisper.cpp 本地识别（自带逐句真实时间戳）→ Claude 通读纠错（同音字 / 专有名词）→ 生成 SRT → ffmpeg + libass 烧录**。

字号 / 字体 / 颜色 / 黑底白字 / 描边均可定制，一套脚本复用于不同视频。

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
| `scripts/srt_to_ass.py` | `cues.json` → ASS（字号 / 字体 / 黑底白字或描边 / 分辨率，字号=真实像素） |
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

完整的 agent 工作流与注意事项见 [`SKILL.md`](SKILL.md)；烧录与识别细节见 [`references/`](references/)。

## 泛化到不同视频

用户只需提供视频（外加可选样式偏好）。`--res` / `--duration` 由 ffprobe 探测；`corrections.txt` 由 Claude 通读该视频转写后自动生成；模型、whisper.cpp、ffmpeg-full 装一次后所有视频复用。非中文改 `whisper-cli -l <code>` 并换对应语言系统字。
