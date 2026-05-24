#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双语 ASS 生成器：中文在上(较大) + 外语原文在下(较小)，二者同一条字幕分两行。
读取双语 cues.json（每条含 start/end/zh/en），按真实像素字号渲染。

样式（--style）:
  box      白字 + 半透明黑色底框（BorderStyle=3，对比最强，醒目）  ← 默认
  outline  白字 + 黑色描边（BorderStyle=1，干净不挡画面）

字号按 --res 的真实像素计；中文用 --zh-size、外文用 --en-size（中文更大更醒目）。
1080p 参考：zh 46~54 / en 32~38（中）；更醒目可加大。其它分辨率按比例：size ≈ 1080p值 × (高/1080)。

用法:
  bi_ass.py --cues cues_bi.json --out bi.ass --style box \
     --zh-size 54 --en-size 38 --res 1920x1080 [--box-alpha 40] [--margin-h 80] [--margin-v 60]

注意：长句要先用 split_long_cues.py 拆成「每条≤1 行中文」，否则中文会折行、字幕一坨。
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
    ap.add_argument("--cues", default="cues_bi.json", help="双语 cues：每条含 zh / en / start / end")
    ap.add_argument("--out", default="bi.ass")
    ap.add_argument("--zh-size", type=int, default=54, help="中文字号(px @ --res)")
    ap.add_argument("--en-size", type=int, default=38, help="外文字号(px @ --res)，通常比中文小")
    ap.add_argument("--font", default="Hiragino Sans GB",
                    help="字体；macOS 中文字幕首选 Hiragino Sans GB（PingFang SC 部分机器无字体文件）")
    ap.add_argument("--res", default="1920x1080", help="须与视频分辨率一致，如 1920x1080 / 2560x1440")
    ap.add_argument("--margin-v", type=int, default=60, help="底边距(px)")
    ap.add_argument("--margin-h", type=int, default=80, help="左右边距(px)")
    ap.add_argument("--style", choices=["outline", "box"], default="box",
                    help="box=白字+半透明黑底框(默认) | outline=白字+黑描边")
    ap.add_argument("--outline", type=int, default=3,
                    help="描边宽度(outline) / 底框内边距(box)")
    ap.add_argument("--box-alpha", default="40",
                    help="底框透明度 hex：00=全不透明 .. FF=全透明（box 样式；数值越小越深）")
    ap.add_argument("--bold", type=int, default=0)
    args = ap.parse_args()

    cues = json.load(open(args.cues, encoding="utf-8"))
    rx, ry = (int(v) for v in args.res.lower().split("x"))

    if args.style == "box":
        # BorderStyle=3 不透明框；把 Outline 与 Back 两个颜色都设成同一半透明黑，
        # 这样无论 libass 用哪个颜色画框，底框都是统一的半透明黑。
        box = f"&H{args.box_alpha}000000"
        borderstyle, outcol, backcol, outline, shadow = 3, box, box, args.outline, 0
    else:
        borderstyle, outcol, backcol, outline, shadow = 1, "&H00000000", "&H00000000", args.outline, 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {rx}
PlayResY: {ry}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{args.font},{args.zh_size},&H00FFFFFF,&H000000FF,{outcol},{backcol},{args.bold},0,0,0,100,100,0,0,{borderstyle},{outline},{shadow},2,{args.margin_h},{args.margin_h},{args.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def esc(s):
        return s.strip().replace("\n", " ").replace("{", "(").replace("}", ")")

    ev = []
    for c in cues:
        zh, en = esc(c["zh"]), esc(c["en"])
        # 第一行(中文)用 zh-size，第二行(外文)用 en-size——同一条 Dialogue 内用 \fs 切换。
        text = f"{{\\fs{args.zh_size}}}{zh}\\N{{\\fs{args.en_size}}}{en}"
        ev.append(f"Dialogue: 0,{t(c['start'])},{t(c['end'])},Default,,0,0,0,,{text}")

    open(args.out, "w", encoding="utf-8").write(header + "\n".join(ev) + "\n")
    print(f"✓ {args.out}: {len(cues)} 条, style={args.style}, zh={args.zh_size}px / en={args.en_size}px, "
          f"font={args.font}, res={rx}x{ry}" + (f", box-alpha={args.box_alpha}" if args.style == "box" else ""))


if __name__ == "__main__":
    main()
