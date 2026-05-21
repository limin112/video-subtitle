#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成交互式字幕核对页（数据内联，可离线 file:// 打开）。

功能：嵌入视频边播边对照；播放时自动高亮跟随；逐条【文字可改】+【时间轴可改】
（⤓设为当前播放位置 / ±0.1s 微调 / ↑↓方向键(Shift=±0.5s) / 直接输入时间 / 起终点联动）；
一键导出修正后的 SRT；可选展示妙记 AI 章节/摘要/关键词。

用法:
  make_review_html.py --cues cues.json --video video.mp4 --out review.html \
      [--title "标题"] [--duration 422.77] [--artifacts notes.json] \
      [--keywords "语音、输入框"] [--correct "callDesk=>Codex" ...]
"""
import json, argparse


def load_notes(path):
    if not path:
        return None
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return None
    i = txt.find("{")
    while i != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(txt[i:])
            return obj
        except Exception:
            i = txt.find("{", i + 1)
    return None


def mmss(t):
    t = float(t)
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True)
    ap.add_argument("--video", default="video.mp4")
    ap.add_argument("--out", default="review.html")
    ap.add_argument("--title", default="字幕核对")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--artifacts", default=None, help="妙记 vc +notes 的 JSON（取 章节/摘要，可选）")
    ap.add_argument("--keywords", default="")
    ap.add_argument("--correct", action="append", default=[])
    args = ap.parse_args()

    cues = json.load(open(args.cues, encoding="utf-8"))
    total = args.duration if args.duration else (cues[-1]["end"] if cues else 0)

    chapters, summary = [], ""
    obj = load_notes(args.artifacts)
    if obj:
        try:
            art = obj["data"]["notes"][0]["artifacts"]
            chapters = art.get("chapters", []) or []
            summary = art.get("summary", "") or ""
        except Exception:
            pass
    for pair in args.correct:
        if "=>" in pair:
            a, b = pair.split("=>", 1)
            summary = summary.replace(a, b)
            for c in chapters:
                c["title"] = c.get("title", "").replace(a, b)
                c["summary_content"] = c.get("summary_content", "").replace(a, b)

    chap_html = ""
    for c in chapters:
        s, e = mmss(int(c["start_ms"]) / 1000), mmss(int(c["stop_ms"]) / 1000)
        chap_html += (f'<div class="chap"><div class="chap-h"><span class="chap-t">{s}–{e}</span>'
                      f'<b>{c.get("title","")}</b></div><p>{c.get("summary_content","")}</p></div>')
    has_ai = bool(chapters or summary or args.keywords)

    tpl = TEMPLATE
    repl = {
        "__TITLE__": args.title,
        "__DUR__": mmss(total),
        "__N__": str(len(cues)),
        "__VIDEO__": args.video,
        "__TOTAL__": f"{total:.3f}",
        "__CHAPTERS__": chap_html or "（无）",
        "__SUMMARY__": summary.replace("&", "&amp;").replace("<", "&lt;") or "（无）",
        "__KW__": args.keywords,
        "__AI_DISPLAY__": "block" if has_ai else "none",
        "__CUES_JSON__": json.dumps(cues, ensure_ascii=False),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    open(args.out, "w", encoding="utf-8").write(tpl)
    print(f"✓ {args.out}: 内联 {len(cues)} 条字幕，AI面板={'有' if has_ai else '无'}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>字幕核对 · __TITLE__</title>
<style>
 :root{--bg:#0f1115;--panel:#171a21;--panel2:#1d2129;--line:#2a2f3a;--txt:#e7e9ee;
   --dim:#9aa3b2;--accent:#5b9dff;--accent2:#ffb454;--ok:#3ecf8e;--hi:#2b3550}
 *{box-sizing:border-box} html,body{margin:0;height:100%}
 body{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
 .wrap{display:grid;grid-template-columns:minmax(380px,40%) 1fr;height:100vh}
 @media(max-width:900px){.wrap{grid-template-columns:1fr;height:auto}}
 .left{position:sticky;top:0;align-self:start;height:100vh;overflow:auto;padding:20px;border-right:1px solid var(--line);background:var(--panel)}
 @media(max-width:900px){.left{position:static;height:auto;border-right:none;border-bottom:1px solid var(--line)}}
 h1{font-size:17px;margin:0 0 4px;font-weight:650} .meta{color:var(--dim);font-size:12.5px;margin-bottom:14px}.meta b{color:var(--accent)}
 .player{position:relative;border-radius:12px;overflow:hidden;background:#000;box-shadow:0 8px 30px rgba(0,0,0,.4)}
 video{width:100%;display:block}
 .ovl{position:absolute;left:0;right:0;bottom:14px;text-align:center;pointer-events:none;padding:0 12px}
 .ovl span{display:inline-block;background:rgba(0,0,0,.62);color:#fff;padding:4px 12px;border-radius:6px;font-size:19px;max-width:94%;text-shadow:0 1px 2px #000}
 .now{margin:12px 2px;font-size:12.5px;color:var(--dim)}.now b{color:var(--accent2)}
 .box{margin-top:14px;border:1px solid var(--line);border-radius:10px;background:var(--panel2)}
 .box>summary{cursor:pointer;padding:11px 14px;font-weight:600;font-size:13.5px;list-style:none;display:flex;justify-content:space-between}
 .box>summary::-webkit-details-marker{display:none}.box .bd{padding:4px 14px 14px;font-size:13px;color:#cdd3df}
 .kw span{display:inline-block;background:#222838;border:1px solid var(--line);color:#bcd;padding:2px 9px;border-radius:20px;font-size:12px;margin:3px 4px 0 0}
 .chap{padding:9px 0;border-top:1px dashed var(--line)}.chap:first-child{border-top:none}
 .chap-h{display:flex;gap:8px;align-items:baseline}.chap-t{font-family:ui-monospace,Menlo,monospace;color:var(--accent);font-size:12px}
 .chap p{margin:2px 0 0;color:var(--dim);font-size:12.5px} pre.sum{white-space:pre-wrap;font-family:inherit;margin:0;color:#cdd3df;font-size:12.8px}
 .right{display:flex;flex-direction:column;height:100vh;min-height:0}@media(max-width:900px){.right{height:auto}}
 .bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:12px 16px;border-bottom:1px solid var(--line);background:var(--panel)}
 .bar .sp{flex:1} button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--panel2);color:var(--txt);padding:7px 12px;border-radius:8px;font-size:13px}
 button:hover{border-color:var(--accent);color:#fff} button.primary{background:var(--accent);border-color:var(--accent);color:#0b1220;font-weight:650}
 .tag{font-size:12px;color:var(--dim)}.tag b{color:var(--ok)}
 .list{overflow:auto;padding:6px 8px 60px;flex:1;min-height:0}@media(max-width:900px){.list{height:auto;overflow:visible}}
 .cue{display:grid;grid-template-columns:200px 1fr;gap:10px;padding:8px 8px;border-radius:9px;border:1px solid transparent;border-left:3px solid transparent}
 .cue:hover{background:#141821}.cue.active{background:var(--hi);border-color:#3a4a78}.cue.edited{border-left-color:var(--accent2)}
 .tcol{display:flex;flex-direction:column;gap:3px}
 .trow{display:flex;align-items:center;gap:3px}.trow.dim .tin{color:var(--dim)}
 .tin{width:62px;font-family:ui-monospace,Menlo,monospace;font-size:11.5px;background:#0c0e12;color:var(--accent);border:1px solid var(--line);border-radius:5px;padding:2px 4px;text-align:center}
 .tin:focus{outline:none;border-color:var(--accent);color:#fff}
 .mini{padding:1px 6px;font-size:12px;border:1px solid var(--line);background:var(--panel2);border-radius:5px;line-height:1.5;color:var(--dim)}
 .mini:hover{border-color:var(--accent);color:#fff} .mini.play{color:var(--accent)} .mini.act{color:var(--accent2)}
 .dur{font-size:10.5px;color:#5b6577;margin-left:2px}
 .tx{font-size:15px;outline:none;border-radius:6px;padding:3px 5px;min-height:1.4em}
 .tx:focus{background:#0c0e12;box-shadow:inset 0 0 0 1px var(--accent)}
 .toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--ok);color:#06281a;padding:10px 18px;border-radius:8px;font-weight:600;opacity:0;transition:.3s;pointer-events:none}
 .toast.show{opacity:1} .hint{padding:9px 16px;color:var(--dim);font-size:12px;border-top:1px solid var(--line)}
 .hint b{color:var(--accent2)}
</style></head><body>
<div class="wrap">
 <div class="left">
  <h1>字幕核对 · __TITLE__</h1>
  <div class="meta">时长 <b>__DUR__</b> · 共 <b>__N__</b> 条 · 边播边对照，文字与时间都可直接改</div>
  <div class="player"><video id="vid" src="__VIDEO__" controls preload="metadata"></video><div class="ovl"><span id="ovl"></span></div></div>
  <div class="now">当前 <b id="nowtc">00:00</b> <span id="nowtx"></span></div>
  <div id="aiwrap" style="display:__AI_DISPLAY__">
   <details class="box"><summary>AI 关键词 <span>›</span></summary><div class="bd kw" id="kw"></div></details>
   <details class="box"><summary>AI 章节纪要 <span>›</span></summary><div class="bd">__CHAPTERS__</div></details>
   <details class="box"><summary>AI 全文摘要 <span>›</span></summary><div class="bd"><pre class="sum">__SUMMARY__</pre></div></details>
  </div>
 </div>
 <div class="right">
  <div class="bar">
   <button class="primary" id="exp">⬇ 导出修正后的 SRT</button>
   <button id="cp">复制全文</button><button id="rst">撤销全部</button>
   <span class="sp"></span>
   <label class="tag"><input type="checkbox" id="follow" checked> 跟随播放</label>
   <label class="tag"><input type="checkbox" id="link" checked> 起终点联动</label>
   <span class="tag">已改 <b id="edcnt">0</b> 条</span>
  </div>
  <div class="list" id="list"></div>
  <div class="hint"><b>改时间：</b>⤓=设为当前播放位置 · −/+ 或 ↑↓方向键=±0.1s（Shift=±0.5s）· 也可直接输入(M:SS.mm 或秒) · ▶=跳到此处。改完点「导出 SRT」发回即可重烧。</div>
 </div>
</div>
<div class="toast" id="toast"></div>
<script>
const CUES=__CUES_JSON__, KW="__KW__", TOTAL=__TOTAL__;
const orig=CUES.map(c=>({text:c.text,start:c.start,end:c.end}));
const vid=document.getElementById('vid'),list=document.getElementById('list'),ovl=document.getElementById('ovl');
const nowtc=document.getElementById('nowtc'),nowtx=document.getElementById('nowtx'),edc=document.getElementById('edcnt');
const fmt=t=>{t=Math.max(0,t);const m=Math.floor(t/60),s=t-m*60;return m+':'+(s<10?'0':'')+s.toFixed(2)};
const fmtClock=t=>{t=Math.max(0,t);return String(Math.floor(t/60)).padStart(2,'0')+':'+String(Math.floor(t%60)).padStart(2,'0')};
const fmtMs=t=>{t=Math.max(0,t);const h=Math.floor(t/3600);t-=h*3600;const m=Math.floor(t/60);t-=m*60;const s=Math.floor(t),ms=Math.round((t-s)*1000);return [h,m,s].map(x=>String(x).padStart(2,'0')).join(':')+','+String(ms).padStart(3,'0')};
const parseT=s=>{s=s.trim();if(s.includes(':')){return s.split(':').reduce((a,p)=>a*60+parseFloat(p),0)}return parseFloat(s)};
const link=()=>document.getElementById('link').checked;
document.getElementById('kw').innerHTML=KW?KW.split(/[、,，]/).filter(Boolean).map(k=>`<span>${k.trim()}</span>`).join(''):'（无）';

CUES.forEach((c,i)=>{const el=document.createElement('div');el.className='cue';el.dataset.i=i;
 el.innerHTML=`<div class="tcol">
   <div class="trow"><button class="mini act" data-act="set" data-edge="start" title="起点设为当前播放位置">⤓</button>
     <input class="tin" data-edge="start"><button class="mini" data-act="nudge" data-edge="start" data-d="-0.1">−</button>
     <button class="mini" data-act="nudge" data-edge="start" data-d="0.1">+</button>
     <button class="mini play" data-act="seek" title="跳到此处播放">▶</button></div>
   <div class="trow dim"><button class="mini act" data-act="set" data-edge="end" title="终点设为当前播放位置">⤓</button>
     <input class="tin" data-edge="end"><button class="mini" data-act="nudge" data-edge="end" data-d="-0.1">−</button>
     <button class="mini" data-act="nudge" data-edge="end" data-d="0.1">+</button><span class="dur"></span></div>
  </div><div class="tx" contenteditable="true" spellcheck="false"></div>`;
 list.appendChild(el);el.querySelector('.tx').innerText=c.text;});
const cueEls=[...document.querySelectorAll('.cue')],txEls=[...document.querySelectorAll('.tx')];
function refresh(i){const el=cueEls[i],c=CUES[i];
 el.querySelector('.tin[data-edge=start]').value=fmt(c.start);
 el.querySelector('.tin[data-edge=end]').value=fmt(c.end);
 el.querySelector('.dur').textContent=(c.end-c.start).toFixed(2)+'s';
 const ed=c.text!==orig[i].text||Math.abs(c.start-orig[i].start)>.001||Math.abs(c.end-orig[i].end)>.001;
 el.classList.toggle('edited',ed);}
CUES.forEach((c,i)=>refresh(i));
const upd=()=>edc.textContent=CUES.filter((c,i)=>c.text!==orig[i].text||Math.abs(c.start-orig[i].start)>.001||Math.abs(c.end-orig[i].end)>.001).length;
function setEdge(i,edge,val){val=Math.max(0,Math.round(val*100)/100);const c=CUES[i];
 if(edge==='start'){const lo=i>0?CUES[i-1].start+0.05:0,hi=c.end-0.05;val=Math.min(Math.max(val,lo),hi);c.start=val;
   if(link()&&i>0){CUES[i-1].end=val;refresh(i-1)}}
 else{const lo=c.start+0.05,hi=i<CUES.length-1?CUES[i+1].end-0.05:TOTAL;val=Math.min(Math.max(val,lo),hi);c.end=val;
   if(link()&&i<CUES.length-1){CUES[i+1].start=val;refresh(i+1)}}
 refresh(i);upd();}
list.addEventListener('click',e=>{const b=e.target.closest('button.mini'),cu=e.target.closest('.cue');if(!cu||!b)return;
 const i=+cu.dataset.i,act=b.dataset.act;
 if(act==='seek'){vid.currentTime=CUES[i].start+0.02;vid.play()}
 else if(act==='set'){setEdge(i,b.dataset.edge,vid.currentTime)}
 else if(act==='nudge'){setEdge(i,b.dataset.edge,CUES[i][b.dataset.edge]+parseFloat(b.dataset.d))}});
list.addEventListener('change',e=>{const inp=e.target.closest('.tin');if(!inp)return;const i=+inp.closest('.cue').dataset.i;
 const v=parseT(inp.value);if(isNaN(v)){refresh(i);return}setEdge(i,inp.dataset.edge,v)});
list.addEventListener('keydown',e=>{const inp=e.target.closest('.tin');if(!inp)return;
 if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();const i=+inp.closest('.cue').dataset.i;
   const step=(e.shiftKey?0.5:0.1)*(e.key==='ArrowUp'?1:-1);setEdge(i,inp.dataset.edge,CUES[i][inp.dataset.edge]+step);
   cueEls[i].querySelector(`.tin[data-edge=${inp.dataset.edge}]`).focus()}});
list.addEventListener('input',e=>{const tx=e.target.closest('.tx');if(!tx)return;const i=+tx.closest('.cue').dataset.i;
 CUES[i].text=tx.innerText.replace(/\n+$/,'');refresh(i);upd()});
let cur=-1;const find=t=>{for(let i=0;i<CUES.length;i++)if(t>=CUES[i].start&&t<CUES[i].end)return i;return -1};
const editing=()=>document.activeElement&&(document.activeElement.classList.contains('tin')||document.activeElement.classList.contains('tx'));
vid.addEventListener('timeupdate',()=>{const t=vid.currentTime;nowtc.textContent=fmtClock(t);const i=find(t);
 if(i!==cur){if(cur>=0)cueEls[cur].classList.remove('active');cur=i;
  if(i>=0){cueEls[i].classList.add('active');ovl.textContent=CUES[i].text;nowtx.textContent=CUES[i].text;
   if(document.getElementById('follow').checked&&!editing())cueEls[i].scrollIntoView({block:'center',behavior:'smooth'})}
  else{ovl.textContent='';nowtx.textContent=''}}});
const buildSRT=()=>CUES.map((c,i)=>(i+1)+'\n'+fmtMs(c.start)+' --> '+fmtMs(c.end)+'\n'+c.text.trim()+'\n').join('\n');
const dl=(n,t)=>{const b=new Blob([t],{type:'text/plain;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=n;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)};
const toast=m=>{const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1800)};
document.getElementById('exp').onclick=()=>{dl('subtitle_corrected.srt',buildSRT());toast('已导出 subtitle_corrected.srt')};
document.getElementById('cp').onclick=()=>navigator.clipboard.writeText(CUES.map(c=>c.text).join('\n')).then(()=>toast('全文已复制'));
document.getElementById('rst').onclick=()=>{if(!confirm('放弃全部修改（文字+时间），恢复原始？'))return;
 CUES.forEach((c,i)=>{c.text=orig[i].text;c.start=orig[i].start;c.end=orig[i].end;txEls[i].innerText=orig[i].text;refresh(i)});upd();toast('已恢复原始')};
</script></body></html>"""


if __name__ == "__main__":
    main()
