# 转写：本地 whisper.cpp（推荐，时间轴准）

相比飞书妙记（只给段落级时间戳，段内靠估算、对不齐），**whisper.cpp 直接输出逐句真实时间戳**的 SRT，是做对齐字幕的首选。Apple Silicon 上走 Metal，7 分钟视频约 30 秒转完。

## 1. 装 whisper.cpp（一次性）
```
brew install whisper-cpp          # 有 arm64 bottle，秒装；提供 whisper-cli，Metal 加速
which whisper-cli                 # /opt/homebrew/bin/whisper-cli
```
> 注意支持的输入是 **wav/mp3/flac/ogg，不是 mp4**——需先抽音轨（见下）。Python 版（faster-whisper/openai-whisper/mlx-whisper）能直接喂 mp4，但它们内部也是调 ffmpeg；且新 Python（如 3.14）这些包的轮子可能没跟上，whisper.cpp 最稳。

## 2. 下载模型（一次性，~1.6GB）
ggml 模型来自 HuggingFace `ggerganov/whisper.cpp`（纯模型数据，非可执行）。**下载属外联操作，先征得用户同意**。
```
mkdir -p ~/.cache/whisper.cpp
curl -L --fail -o ~/.cache/whisper.cpp/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```
- `large-v3-turbo`(~1.6GB) 速度快中文准，推荐；`large-v3`(~3.1GB) 最准稍慢；`medium`(~1.5GB) 中文偏弱。

## 3. 抽 16k 单声道音轨
```
/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -y -i video.mp4 -ar 16000 -ac 1 -c:a pcm_s16le audio16k.wav
```
（普通 ffmpeg 也能抽音频；不需要 libass。）

## 4. 识别 → SRT（带真实时间戳）
```
M=~/.cache/whisper.cpp/ggml-large-v3-turbo.bin
whisper-cli -m "$M" -f audio16k.wav -l zh -osrt -of video_whisper \
   --prompt "AI First、Codex" -t 8
```
- **不要加 `-ml`**：默认按自然停顿断句，行干净（短句一行、各自带时间戳）。`-ml N` 会按字数硬切，把短语断在词中间（如「Codex实」+「战课」），仅在确实需要更碎时才用。
- `--prompt "<专有名词，顿号分隔>"`：把已知专有名词喂进去，显著降低听错（本例让它正确输出 `Codex` 而非 `callDesk`）。已有飞书文字时，可从中提取专有名词做 prompt。
- `-l zh` 中文；`-t 8` 线程；large-v3 默认输出简体、自带逗号。

## 5. 接入现有流程
whisper 出的是 SRT，转成统一的 cues.json 再走核对/烧录：
```
python3 scripts/srt_to_cues.py --srt video_whisper.srt --cues cues.whisper.json
python3 scripts/make_review_html.py --cues cues.whisper.json --video video.mp4 --out review.html --duration <秒>
python3 scripts/srt_to_ass.py --cues cues.whisper.json --out video.ass --fontsize 48 --style box
# 然后用 ffmpeg-full 烧录（见 burn-in-ffmpeg.md）
```

## whisper.cpp vs 飞书妙记 怎么选
- **要时间轴对齐 / 本地私密 / 快** → whisper.cpp（本文）。逐句真实时间戳，无需 align_to_speech.py。
- **要最好的中文文字 / 顺带 AI 章节摘要** → 飞书妙记（[transcribe-feishu.md](transcribe-feishu.md)），但时间是段落级，需 transcript_to_srt.py + align_to_speech.py 逼近。
- **两者结合**：用飞书的好文字 + whisper 的好时间（强制对齐），最准但最复杂；多数情况 whisper.cpp 重转 + 核对页改几个错别字即可。
- whisper 偶有同音/近音错（如「程序员」听成「程序儿」），在核对页 review.html 改即可。
