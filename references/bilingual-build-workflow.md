# 双语字幕：构建脚本工作流（纠错 + 翻译 + 时间修正 + 删条，可复现）

双语视频的「纠错 + 翻译」是你（Claude）的逐视频工件，量大（几百条）、又需要可复现、可局部返工。
**别手写 `cues_bi.json`**（条数多、JSON 易错、改一条还要对齐时间戳）。改用一个 build 脚本承载四件套，
按 `idx` 从 whisper 的 `cues_en.json` 合并出 `cues_bi.json`：

- **`CORR`**：英文识别纠错表（有序 dict，**先长/特定短语、后通用**，区分大小写）。例：把误听的 `"Cloud Code"→"Claude Code"`、人名拼写统一替换。
- **`ZH`**：按 `cues_en.json` 顺序的逐条中文译文（list，长度**必须等于** cues 数，用 `assert` 卡住）。
- **`TIME_OVERRIDE`**：个别条的 `(start,end)` 覆写——**改时间不必重译**（如开场被音乐/掌声带偏的几条）。
- **`DROP`**：要删除的 `idx` 集合（如音乐段的幻觉字幕条）。
- （可选）**`EN_OVERRIDE`**：个别条整句覆写英文（CORR 的字符串替换搞不定的复杂情形）。

好处：「只修开场 6 条时间 + 删 4 条幻觉、保留其余 400+ 翻译」只动几行、可整段重跑，结果稳定。

## 流程
1. `srt_to_cues.py --srt video_whisper.srt --cues cues_en.json` → 带 `idx` 的英文 cues。
2. 你通读 `cues_en.json`，写出下面的 build 脚本（填 `CORR`/`ZH`/`TIME_OVERRIDE`/`DROP`），运行得 `cues_bi.json`。
3. `split_bi_cues.py` 拆行（中英都顾）→ `bi_ass.py` 生成 ASS → ffmpeg 烧录（见 SKILL.md / burn-in-ffmpeg.md）。

## 模板（按视频改 CORR / ZH / TIME_OVERRIDE / DROP）
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
WORK = "."

CORR = {                       # 英文识别纠错（顺序敏感：长/特定短语在前）
    "Cloud Code": "Claude Code",
    # "误听词": "正确词", ...
}
EN_OVERRIDE = {}               # 个别条整句覆写英文：{idx: "corrected en"}
TIME_OVERRIDE = {}             # 个别条改时间：{idx: (start, end)}
DROP = set()                   # 删除的 idx（音乐/掌声段幻觉字幕等）

ZH = [                         # 按 cues_en.json 顺序，逐条中文译文（数量必须正好等于 cues 数）
    "……",                     # 1
    # ...
]

cues = json.load(open(WORK + "/cues_en.json", encoding="utf-8"))
assert len(ZH) == len(cues), f"ZH {len(ZH)} != cues {len(cues)}"
out = []
for c, z in zip(cues, ZH):
    if c["idx"] in DROP:
        continue
    en = EN_OVERRIDE.get(c["idx"], c["text"])
    for a, b in CORR.items():
        en = en.replace(a, b)
    start, end = TIME_OVERRIDE.get(c["idx"], (c["start"], c["end"]))
    out.append({"start": start, "end": end, "en": en.strip(), "zh": z})
json.dump(out, open(WORK + "/cues_bi.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"✓ cues_bi.json: {len(out)} 条")
```

## 配套：TIME_OVERRIDE 的时间从哪来
开场/结尾的音乐·掌声会让 whisper 把人声计时往前压（字幕偏早），中后段连续对话通常已准（见
[`transcribe-whisper.md`](transcribe-whisper.md) 的 VAD 一节）。拿准确时间的办法：
- 对开场单独跑 **VAD / 细粒度 VAD** 读出每句真实时间；或
- 用 `ffmpeg silencedetect` 找真实语音起点，对照 whisper 时间戳定位偏差。

把准确时间填进 `TIME_OVERRIDE`、把音乐段幻觉条放进 `DROP`，即可**只改开场、不动其余翻译**。
