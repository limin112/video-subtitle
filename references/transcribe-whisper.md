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

## VAD：开场/结尾有音乐·掌声时（修幻觉 + 修计时偏早）
whisper.cpp 在**音乐 / 掌声 / 长非语音**段有两个老问题：
1. **幻觉字幕**：把音乐听成反复的短句（如每 30s 一条 “We'll be right back.”）。
2. **计时偏早**：把随后真人语音的时间戳整体往前压——字幕比说话早好几秒（开场尤其明显；中后段连续对话通常正常）。

开启 VAD（语音活动检测）对齐真实语音、自动跳过非语音：
```
M=~/.cache/whisper.cpp/ggml-large-v3-turbo.bin
VAD=~/.cache/whisper.cpp/ggml-silero-v5.1.2.bin
# 模型 ~864KB，来自 HuggingFace ggml-org/whisper-vad，外联需用户同意，一次性下：
# curl -L --fail -o "$VAD" https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin
whisper-cli -m "$M" -f audio16k.wav -l en --vad -vm "$VAD" -osrt -of video_whisper -t 8
```
- **代价**：VAD 可能漏掉夹在掌声里的**极短句**（如 “Hello.” “All right.”）。若在意，对开场单独跑**细粒度 VAD**拿每句时间：
  ```
  ffmpeg -y -i audio16k.wav -t 135 -c copy intro.wav     # 截开场
  whisper-cli -m "$M" -f intro.wav -l en --vad -vm "$VAD" -vmsd 5 -vsd 200 -vt 0.4 -osrt -of intro
  ```
  `-vmsd` 最大段秒数（强制切短）/ `-vsd` 最小静音 ms（越小越爱切）/ `-vt` 阈值（越低越敏感）。
- **诊断真实语音起点**（不重识别也能定位偏差）：
  ```
  ffmpeg -hide_banner -nostats -i audio16k.wav -t 130 -af "silencedetect=noise=-30dB:d=0.4" -f null -
  ```
  对比 whisper 的段起始时间与 `silence_end`（语音起点），就能量出偏早多少秒。
- **局部修而不重译（重要）**：若只是开场几条偏了，**别全量换 VAD 版**——VAD 会改变分段、得重做翻译。中后段计时通常已准，只把开场几条的准确时间填进双语 build 脚本的 `TIME_OVERRIDE`、把音乐幻觉条放进 `DROP` 即可（见 [`bilingual-build-workflow.md`](bilingual-build-workflow.md)）。

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
