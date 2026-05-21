#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cues.json -> ASS 字幕，坐标固定为视频分辨率（字号=真实像素，便于精确控制）。

用法:
  srt_to_ass.py --cues cues.json --out video.ass --fontsize 48 \
      [--font "Hiragino Sans GB"] [--style box|outline] [--res 1920x1080] [--margin-v N]

样式:
  box     黑底白字（不透明黑框，BorderStyle=3）
  outline 白字黑描边（BorderStyle=1，默认）
"""
import json, argparse


def t(x):
    h = int(x // 3600); x -= h * 3600
    m = int(x // 60);   x -= m * 60
    s = int(x);         cs = int(round((x - s) * 100))
    if cs == 100:
        s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True, help="cues.json（含 start/end/text）")
    ap.add_argument("--out", required=True, help="输出 .ass 路径")
    ap.add_argument("--fontsize", type=int, default=48, help="字号(px, 基于 --res 的纵向像素)")
    ap.add_argument("--font", default="Hiragino Sans GB",
                    help="字体名（libass 经 fontconfig 解析；中文系统字常用 Hiragino Sans GB / STHeiti / Songti SC）")
    ap.add_argument("--style", choices=["box", "outline"], default="box",
                    help="box=黑底白字(默认) | outline=白字黑描边")
    ap.add_argument("--res", default="1920x1080", help="字幕坐标分辨率，应与视频一致，如 1920x1080")
    ap.add_argument("--margin-v", type=int, default=None, help="底边距(px)，默认≈字号*1.1")
    args = ap.parse_args()

    cues = json.load(open(args.cues, encoding="utf-8"))
    rx, ry = (int(v) for v in args.res.lower().split("x"))
    fs = args.fontsize

    if args.style == "box":
        borderstyle, outline, shadow = 3, max(3, round(fs / 12)), 0   # 不透明黑框
    else:
        borderstyle, outline, shadow = 1, max(1, round(fs / 18)), 1   # 描边
    marginv = args.margin_v if args.margin_v is not None else max(30, round(fs * 1.1))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {rx}
PlayResY: {ry}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{fs},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,{borderstyle},{outline},{shadow},2,60,60,{marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def esc(s):
        return s.strip().replace("\n", r"\N")
    ev = [f"Dialogue: 0,{t(c['start'])},{t(c['end'])},Default,,0,0,0,,{esc(c['text'])}"
          for c in cues]
    open(args.out, "w", encoding="utf-8").write(header + "\n".join(ev) + "\n")
    print(f"✓ {args.out}: style={args.style}, fontsize={fs}px, font={args.font}, "
          f"res={rx}x{ry}, outline={outline}, {len(cues)} 条")


if __name__ == "__main__":
    main()
