# 烧录硬字幕：ffmpeg + libass + 字体

把字幕永久烧进画面（硬字幕）。核心是一个**带 libass** 的 ffmpeg。

## 1. 检查 / 获取带 libass 的 ffmpeg
```
ffmpeg -hide_banner -filters | grep -w subtitles      # 空 = 没有 libass，烧不了
ffmpeg -hide_banner -version | grep -oE "enable-(libass|libfreetype|fontconfig)"
```
macOS 上 Homebrew 默认的 `ffmpeg` 常是**精简 bottle**（无 libass / freetype / fontconfig，连 `drawtext` 都没有）。

**正确解法（秒装、可信、无副作用）：**
```
brew install ffmpeg-full        # homebrew/core 的完整版，有 arm64 预编译 bottle，含 libass/fontconfig/freetype/harfbuzz
```
- 它是 **keg-only**，与现有 `ffmpeg` 并存，二进制在 `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`（和 ffprobe）。后续烧录都用这个全路径，不影响系统默认 ffmpeg。

**不要走的弯路（本项目踩过）：**
- ❌ `brew install homebrew-ffmpeg/ffmpeg/ffmpeg`：需**先卸载** core ffmpeg（同名冲突），且**从源码编译**，常因 `Error: Your Command Line Tools are too outdated`（要新版 Xcode CLT）而失败，编译期间还没有 ffmpeg 可用。若已误删 core ffmpeg：`brew install ffmpeg` 可秒速还原（bottle）。
- ❌ App 内嵌的 ffmpeg（如某些剪辑软件 .app/Contents/Resources/ffmpeg）：常被签名限制（裸跑 exit 133/SIGTRAP）且多半无 subtitles 滤镜，不可靠。
- ❌ 下载第三方静态二进制：可行但属"下载并运行外部可执行文件"，需用户明确同意，优先用 `ffmpeg-full`。

## 2. 字体（"系统字" / 中文）
- macOS 中文"系统字"名义上是 **PingFang SC**，但**部分机器无 `/System/Library/Fonts/PingFang.ttc`**。
- libass 经 **fontconfig** 按名字找字体。用 `fc-match` 看实际解析：
  ```
  fc-match "PingFang SC"     # 本项目机器上回退到 -> Hiragino Sans GB.ttc（冬青黑体简体中文）
  fc-match "Hiragino Sans GB"; fc-match "Heiti SC"; fc-match "Songti SC"
  ```
- 字幕推荐黑体类：**Hiragino Sans GB**（干净、PingFang 的天然回退）、STHeiti、或宋体 Songti SC。在 `srt_to_ass.py --font` 里传名字即可。

## 3. 生成样式可控的 ASS，再烧
用 `scripts/srt_to_ass.py` 生成 ASS（**PlayResX/Y 固定为视频分辨率，字号即真实像素**，可精确控制）：
```
python3 scripts/srt_to_ass.py --cues cues.aligned.json --out video.ass \
   --fontsize 48 --style box --font "Hiragino Sans GB" --res 1920x1080
```
- `--style box`：黑底白字（ASS `BorderStyle=3` 不透明框，白字）。
- `--style outline`：白字黑描边（`BorderStyle=1`）。
- 字号：1080p 上 28≈小 / 40≈中 / 52≈大。用户说"几号字"难直接换算像素时，渲染几档样片让其挑。

烧录：
```
FF=/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg
"$FF" -y -i video.mp4 -vf "ass=video.ass" \
   -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
   -c:a copy -movflags +faststart "成片_字幕版.mp4"
```
- `ass=video.ass`（不是 `subtitles=`）能用 ASS 里固定的 PlayRes，样式最可控。
- `-c:a copy` 音轨不重编码；`crf 20` 清晰且体积小；`yuv420p` 兼容性；`+faststart` 利于网页/移动播放。
- 也可用 `-c:v h264_videotoolbox -b:v <码率>` 走 M 芯片硬件编码提速，但码率控制不如 libx264 crf 精细。

## 4. 烧录前必做：样片确认
整段重编码慢，先抽一帧给用户看字号/样式/字体对不对：
```
"$FF" -loglevel error -i video.mp4 -vf "ass=video.ass" -ss 4 -frames:v 1 -y sample.png
```
（`-ss` 放 `-i` 后用输出端定位，字幕时间能对上；选一个有较长字幕的时间点。）确认后再跑整段，必要时放后台。

## 5. 验证成片
```
FP=/opt/homebrew/opt/ffmpeg-full/bin/ffprobe
"$FP" -v error -show_entries format=duration:stream=codec_type,codec_name,width,height -of default=noprint_wrappers=1 "成片_字幕版.mp4"
# 从成片本身抽帧确认字幕已烧入（非实时叠加）：
"$FF" -loglevel error -ss 20 -i "成片_字幕版.mp4" -frames:v 1 -y verify.png
```
核对：时长与原片一致、视频 h264 / 音频 aac、抽帧能看到字幕。
