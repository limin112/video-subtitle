#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双语字幕拆分（中英都顾）：当中文行 OR 外文行在各自字号下超出可用宽度时继续拆，
保证拆后每条的中文、外文各自都 ≤1 行（不折行、不超左右边距）。

相比 split_long_cues.py（只看中文宽度），本脚本同时约束外文行——字号一大时，
外文行最容易被 libass 折成两行 / 糊成一坨。要点：
  · 中文 OR 外文任一行超 usable 就继续拆（fits 即停）；
  · token 保护：尽量不在英文/数字 token 内部断行（CLAUDE.md、HTTP/3、4.7、await 等）；
  · 已超宽的条目必须拆到底（不被最小时长提前放弃），仅时长极小(<=0.2s)才停。
中文在最接近行中点的标点/字符边界断、外文按比例在词边界断、时间按中文长度切分。

用法（--zh-size/--en-size/--res/--margin-h 必须与 bi_ass.py 完全一致，阈值才和真实换行对得上）:
  split_bi_cues.py --in cues_bi.json --out cues_bi_split.json \
     --zh-size 60 --en-size 41 --res 1920x1080 --margin-h 80
运行末尾打印「仍超宽: N」，正常应为 0。
"""
import json, argparse, unicodedata

PUNCT = "，。、；：！？,.;:!?…— 　"  # 优先断点（中英标点 + 半/全角空格）


def cjk(ch):
    return unicodedata.east_asian_width(ch) in ("W", "F")


def w(s, fs):  # 渲染宽度：CJK≈1em，其它≈0.5em
    return sum(fs if cjk(c) else fs * 0.5 for c in s)


def tokchar(c):
    return c.isalnum() or c in "./-_'"


def best_zh_split(zh, fs):
    """靠近中点断；优先标点/空格，其次普通字符边界，尽量不在英文/数字 token 内部断
    （保护 CLAUDE.md、HTTP/3、4.7、await 等）。用惩罚分而非硬跳过，保证仍取中点附近。"""
    target = w(zh, fs) / 2
    best_i, best = None, None
    acc = 0.0
    for i in range(len(zh) - 1):
        ch, nxt = zh[i], zh[i + 1]
        acc += fs if cjk(ch) else fs * 0.5
        if tokchar(ch) and tokchar(nxt):
            pen = 10 ** 12          # token 内部：基本不在此断
        elif ch in PUNCT:
            pen = 0                 # 标点/空格：最优
        else:
            pen = 10 ** 6           # 普通字符边界：次之
        score = abs(acc - target) + pen
        if best is None or score < best:
            best, best_i = score, i + 1
    return best_i


def split_en(en, frac):
    """在最接近 frac 比例的词边界处把外文断成两段。"""
    words = en.split()
    if len(words) <= 1:
        return en, ""
    target = len(en) * frac
    best_k, best = 1, None
    for k in range(1, len(words)):
        d = abs(len(" ".join(words[:k])) - target)
        if best is None or d < best:
            best, best_k = d, k
    return " ".join(words[:best_k]), " ".join(words[best_k:])


def fits(c, zfs, efs, usable):
    return w(c["zh"], zfs) <= usable and w(c["en"], efs) <= usable


def split_cue(c, zfs, efs, usable, depth=0):
    # 超宽（中文或外文任一行）就继续拆；fits 即停。深度上限放宽到 10。
    if fits(c, zfs, efs, usable) or depth >= 10:
        return [c]
    i = best_zh_split(c["zh"], zfs)
    if not i:
        return [c]
    zh1, zh2 = c["zh"][:i].strip(), c["zh"][i:].strip()
    if not zh1 or not zh2:
        return [c]
    if c["end"] - c["start"] <= 0.2:   # 时长极小不再拆，避免 0 时长字幕
        return [c]
    frac = w(zh1, zfs) / w(c["zh"], zfs)
    en1, en2 = split_en(c["en"], frac)
    mid = c["start"] + (c["end"] - c["start"]) * frac
    a = {"start": c["start"], "end": mid, "zh": zh1, "en": en1}
    b = {"start": mid, "end": c["end"], "zh": zh2, "en": en2}
    return split_cue(a, zfs, efs, usable, depth + 1) + split_cue(b, zfs, efs, usable, depth + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="cues_bi.json")
    ap.add_argument("--out", default="cues_bi_split.json")
    ap.add_argument("--zh-size", type=int, required=True)
    ap.add_argument("--en-size", type=int, required=True)
    ap.add_argument("--res", required=True, help="须与 bi_ass.py 一致，如 1920x1080")
    ap.add_argument("--margin-h", type=int, default=80)
    ap.add_argument("--safety", type=float, default=0.95, help="可用宽度安全系数（留边，防贴边折行）")
    args = ap.parse_args()

    rx = int(args.res.lower().split("x")[0])
    usable = (rx - 2 * args.margin_h) * args.safety
    cues = json.load(open(args.inp, encoding="utf-8"))
    out = []
    for c in cues:
        out += split_cue({"start": c["start"], "end": c["end"], "zh": c["zh"], "en": c["en"]},
                         args.zh_size, args.en_size, usable)
    for i, c in enumerate(out, 1):
        c["idx"] = i
        c["text"] = c["zh"] + "\n" + c["en"]
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    over = sum(1 for c in out if w(c["en"], args.en_size) > usable or w(c["zh"], args.zh_size) > usable)
    print(f"✓ {args.out}: {len(cues)} -> {len(out)} 条 | usable={usable:.0f}px | 仍超宽: {over}")


if __name__ == "__main__":
    main()
