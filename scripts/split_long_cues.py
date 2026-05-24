#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把过长的双语字幕拆短，保证每条中文在给定字号/分辨率下 ≤1 行（不折行）。

读取双语 cues.json（每条 start/end/zh/en）→ 写出拆分后的 cues.json：
  - 中文在「最接近行中点的标点」处断开（，。、；：！？,.;:!? 空格 …—），无标点则就近断；
  - 外文在「对应比例处的词边界」断开；
  - 时间按中文长度比例切分；
  - 半行若仍超长则递归再拆；过短(<--min-dur)则不拆。

务必用与 bi_ass.py 相同的 --zh-size / --res / --margin-h，拆分阈值才与真实换行一致。

用法:
  split_long_cues.py --in cues_bi.json --out cues_bi_split.json \
     --zh-size 54 --res 1920x1080 [--margin-h 80] [--min-dur 0.8]

自动拆分是「足够好」的基线；个别重要句子若想在更自然的语义点断开，可由 Claude 手改结果。
"""
import json, argparse, unicodedata

PUNCT = "，。、；：！？,.;:!?…— 　"  # 优先断点（中英标点 + 空格/全角空格）


def cjk(ch):
    return unicodedata.east_asian_width(ch) in ("W", "F")


def zh_w(s, fs):  # 渲染宽度：CJK≈1em，其它≈0.5em
    return sum(fs if cjk(c) else fs * 0.5 for c in s)


def best_zh_split(zh, fs, usable):
    """返回中文断开下标：尽量在标点后、且最接近行宽中点。
    只在「字符之间」断（下标 1..len-1），绝不在末字符之后断（否则末尾句号会被当断点→空后半段→不拆）。"""
    target = zh_w(zh, fs) / 2
    best_i, best_score, acc = None, None, 0.0
    for index in range(len(zh) - 1):       # 断在 index 之后 → 后半段必非空
        ch = zh[index]
        acc += fs if cjk(ch) else fs * 0.5
        bonus = 0 if ch in PUNCT else usable  # 标点强烈优先
        score = abs(acc - target) + bonus
        if best_score is None or score < best_score:
            best_score, best_i = score, index + 1
    return best_i


def split_en(en, frac):
    """在最接近 frac 比例的词边界处把外文断成两段。"""
    words = en.split()
    if len(words) <= 1:
        return en, ""
    target = len(en) * frac
    best_k, best_d = 1, None
    for k in range(1, len(words)):
        d = abs(len(" ".join(words[:k])) - target)
        if best_d is None or d < best_d:
            best_d, best_k = d, k
    return " ".join(words[:best_k]), " ".join(words[best_k:])


def split_cue(c, fs, usable, min_dur, depth=0):
    if zh_w(c["zh"], fs) <= usable or depth >= 4:
        return [c]
    i = best_zh_split(c["zh"], fs, usable)
    zh1, zh2 = c["zh"][:i].strip(), c["zh"][i:].strip()
    if not zh1 or not zh2:
        return [c]
    frac = zh_w(zh1, fs) / zh_w(c["zh"], fs)
    dur = c["end"] - c["start"]
    if dur * frac < min_dur or dur * (1 - frac) < min_dur:
        return [c]  # 不制造过短字幕
    en1, en2 = split_en(c["en"], frac)
    mid = c["start"] + dur * frac
    a = {"start": c["start"], "end": mid, "zh": zh1, "en": en1}
    b = {"start": mid, "end": c["end"], "zh": zh2, "en": en2}
    return split_cue(a, fs, usable, min_dur, depth + 1) + split_cue(b, fs, usable, min_dur, depth + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="cues_bi.json")
    ap.add_argument("--out", default="cues_bi_split.json")
    ap.add_argument("--zh-size", type=int, default=54)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--margin-h", type=int, default=80)
    ap.add_argument("--min-dur", type=float, default=0.8)
    args = ap.parse_args()

    rx = int(args.res.lower().split("x")[0])
    usable = rx - 2 * args.margin_h
    cues = json.load(open(args.inp, encoding="utf-8"))
    out = []
    for c in cues:
        out += split_cue({"start": c["start"], "end": c["end"], "zh": c["zh"], "en": c["en"]},
                         args.zh_size, usable, args.min_dur)
    for i, c in enumerate(out, 1):
        c["idx"] = i
        c["text"] = c["zh"] + "\n" + c["en"]
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✓ {args.out}: {len(cues)} -> {len(out)} 条 (+{len(out) - len(cues)}); "
          f"zh={args.zh_size}px usable={usable}px")


if __name__ == "__main__":
    main()
