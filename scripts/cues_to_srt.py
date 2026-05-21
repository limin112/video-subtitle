#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cues.json -> SRT。用于把（核对/纠错后的）cues 导出成标准 SRT 字幕文件。

用法: cues_to_srt.py --cues cues.json --srt out.srt
"""
import json, argparse


def fmt(t, sep=","):
    t = max(0, t)
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60);   t -= m * 60
    s = int(t);         ms = int(round((t - s) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True)
    ap.add_argument("--srt", default="subtitle.srt")
    args = ap.parse_args()
    cues = json.load(open(args.cues, encoding="utf-8"))
    cues.sort(key=lambda c: c["start"])
    with open(args.srt, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{fmt(c['start'])} --> {fmt(c['end'])}\n{c['text'].strip()}\n\n")
    print(f"✓ {args.srt}: {len(cues)} 条")


if __name__ == "__main__":
    main()
