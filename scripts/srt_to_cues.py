#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SRT -> cues.json（idx/start/end/text，时间为秒），可同时应用纠错。

把任意来源的 SRT（如 whisper.cpp 输出）转成本流程统一的 cues.json，
并可应用「识别纠错」（同音字、专有名词等）——纠错由调用方（Claude 通读后判断）给出。

用法:
  srt_to_cues.py --srt video_whisper.srt --cues cues.json \
     [--corrections-file corrections.txt] [--correct "错=>对" ...] [--out-srt corrected.srt]

corrections-file 每行一条 "错词=>对词"，# 开头为注释，空行忽略。
--correct 可重复，与文件合并。所有修正按出现顺序对每条字幕文本做字符串替换。
"""
import re, json, argparse


def parse_ts(s):
    s = s.strip()
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))


def fmt_ts(t, sep=","):
    t = max(0, t)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60);   t -= m * 60
    s = int(t);         ms = int(round((t - s) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def load_corrections(args):
    pairs = []
    if args.corrections_file:
        for line in open(args.corrections_file, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "=>" in line:
                a, b = line.split("=>", 1)
                pairs.append((a.strip(), b.strip()))
    for c in args.correct:
        if "=>" in c:
            a, b = c.split("=>", 1)
            pairs.append((a.strip(), b.strip()))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--cues", default="cues.json")
    ap.add_argument("--corrections-file", default=None)
    ap.add_argument("--correct", action="append", default=[])
    ap.add_argument("--out-srt", default=None, help="同时写出纠错后的 SRT")
    args = ap.parse_args()

    pairs = load_corrections(args)

    txt = open(args.srt, encoding="utf-8-sig").read()
    cues, n_fix = [], 0
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = [x for x in block.splitlines() if x.strip()]
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None:
            continue
        m = re.search(r"([\d:,.]+)\s*-->\s*([\d:,.]+)", lines[ti])
        if not m:
            continue
        text = " ".join(lines[ti + 1:]).strip()
        if not text:
            continue
        for a, b in pairs:
            if a and a in text:
                text = text.replace(a, b); n_fix += 1
        cues.append({"start": parse_ts(m.group(1)), "end": parse_ts(m.group(2)), "text": text})
    for i, c in enumerate(cues):
        c["idx"] = i + 1

    json.dump(cues, open(args.cues, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if args.out_srt:
        with open(args.out_srt, "w", encoding="utf-8") as f:
            for i, c in enumerate(cues, 1):
                f.write(f"{i}\n{fmt_ts(c['start'])} --> {fmt_ts(c['end'])}\n{c['text']}\n\n")

    span = f"{cues[0]['start']:.2f}–{cues[-1]['end']:.2f}s" if cues else "空"
    print(f"✓ {args.cues}: {len(cues)} 条 | 跨度 {span} | 应用纠错 {len(pairs)} 条规则、命中替换 {n_fix} 处"
          + (f" | 同时写出 {args.out_srt}" if args.out_srt else ""))


if __name__ == "__main__":
    main()
