import os
import json
import re
import random
import subprocess
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

OUTPUT_DIR = "output/thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Konu → Renk şeması ───────────────────────────────────────
TOPIC_STYLES = {
    "electric_vehicle": {
        "bg":       "#000000",
        "left_bg":  "#0a0000",
        "right_bg": "#000a18",
        "accent1":  "#ff2200",
        "accent2":  "#00d4ff",
        "glow1":    "rgba(255,30,0,0.35)",
        "glow2":    "rgba(0,180,255,0.30)",
        "label":    "EV DATA",
        "icon":     "⚡",
    },
    "battery_tech": {
        "bg":       "#000000",
        "left_bg":  "#0a0500",
        "right_bg": "#000a05",
        "accent1":  "#ff6b00",
        "accent2":  "#00ff88",
        "glow1":    "rgba(255,107,0,0.35)",
        "glow2":    "rgba(0,255,136,0.25)",
        "label":    "BATTERY",
        "icon":     "🔋",
    },
    "artificial_intelligence": {
        "bg":       "#000000",
        "left_bg":  "#05000a",
        "right_bg": "#00000a",
        "accent1":  "#8b00ff",
        "accent2":  "#00d4ff",
        "glow1":    "rgba(139,0,255,0.35)",
        "glow2":    "rgba(0,212,255,0.25)",
        "label":    "AI TECH",
        "icon":     "🤖",
    },
    "robotics": {
        "bg":       "#000000",
        "left_bg":  "#000a00",
        "right_bg": "#000505",
        "accent1":  "#00ff88",
        "accent2":  "#ffffff",
        "glow1":    "rgba(0,255,136,0.30)",
        "glow2":    "rgba(255,255,255,0.15)",
        "label":    "ROBOTICS",
        "icon":     "🦾",
    },
    "future_tech": {
        "bg":       "#000000",
        "left_bg":  "#05000a",
        "right_bg": "#0a0005",
        "accent1":  "#ff00ff",
        "accent2":  "#ffcc00",
        "glow1":    "rgba(255,0,255,0.30)",
        "glow2":    "rgba(255,204,0,0.25)",
        "label":    "FUTURE",
        "icon":     "🚀",
    },
    "default": {
        "bg":       "#000000",
        "left_bg":  "#0a0000",
        "right_bg": "#000a18",
        "accent1":  "#ff2200",
        "accent2":  "#00d4ff",
        "glow1":    "rgba(255,30,0,0.35)",
        "glow2":    "rgba(0,180,255,0.30)",
        "label":    "EV TECH",
        "icon":     "⚡",
    },
}

# ── Farklı layout şablonları ──────────────────────────────────
LAYOUTS = ["split", "versus", "shock", "data"]


def _safe_text(text: str, max_len: int = 25) -> str:
    text = re.sub(r"['\"`\\]", "", text)
    text = re.sub(r"[^\w\s%\-\+\?!.,:/]", "", text)
    return text[:max_len].strip()


def _split_title(title: str):
    """Başlığı 3 satıra böl, her satır max 3 kelime."""
    words = title.upper().split()
    fillers = {"IN","THE","A","AN","AND","OR","OF","FOR","TO","IS","ARE","WAS","BUT","WITH"}
    if len(words) > 9:
        words = [w for w in words if w not in fillers]

    lines, chunk = [], []
    for word in words:
        chunk.append(word)
        if len(chunk) == 3:
            lines.append(" ".join(chunk))
            chunk = []
            if len(lines) == 3:
                break
    if chunk and len(lines) < 3:
        lines.append(" ".join(chunk))
    while len(lines) < 2:
        lines.append("")
    return [_safe_text(l) for l in lines[:3]]


def _build_html(title: str, topic: str, layout: str) -> str:
    style = TOPIC_STYLES.get(topic, TOPIC_STYLES["default"])
    lines = _split_title(title)
    l1 = lines[0] if len(lines) > 0 else "EV"
    l2 = lines[1] if len(lines) > 1 else "TECH"
    l3 = lines[2] if len(lines) > 2 else ""

    a1  = style["accent1"]
    a2  = style["accent2"]
    g1  = style["glow1"]
    g2  = style["glow2"]
    lbl = style["label"]
    ico = style["icon"]

    if layout == "split":
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;overflow:hidden;background:#000}}
.wrap{{width:1280px;height:720px;position:relative;overflow:hidden;
  background:linear-gradient(135deg,{style['left_bg']} 0%,#000 45%,{style['right_bg']} 100%)}}
.gl{{position:absolute;left:-100px;top:-100px;width:800px;height:800px;
  background:radial-gradient(circle,{g1} 0%,transparent 60%);filter:blur(30px)}}
.gr{{position:absolute;right:-100px;bottom:-100px;width:700px;height:700px;
  background:radial-gradient(circle,{g2} 0%,transparent 60%);filter:blur(30px)}}
.divider{{position:absolute;top:0;left:0;width:100%;height:100%;
  background:linear-gradient(105deg,transparent 48%,{a1}99 49.5%,{a2}99 50.5%,transparent 52%)}}
.left{{position:absolute;left:0;top:0;width:640px;height:720px;
  display:flex;flex-direction:column;justify-content:center;padding:40px 40px 40px 70px}}
.badge{{display:inline-flex;align-items:center;background:{a1};
  padding:8px 20px;margin-bottom:20px;width:fit-content}}
.badge span{{font-family:Arial Black,sans-serif;font-size:24px;font-weight:900;
  color:#fff;letter-spacing:4px}}
.t1{{font-family:Arial Black,sans-serif;font-size:148px;font-weight:900;
  line-height:0.82;letter-spacing:-4px;text-transform:uppercase;color:{a1};
  text-shadow:0 0 50px {a1}cc,4px 4px 0 #000}}
.t2{{font-family:Arial Black,sans-serif;font-size:148px;font-weight:900;
  line-height:0.82;letter-spacing:-4px;text-transform:uppercase;color:#fff;
  text-shadow:0 0 20px {a1}66,4px 4px 0 #000;position:relative}}
.strike{{position:absolute;top:52%;left:-15px;right:-10px;height:14px;
  background:linear-gradient(90deg,transparent,{a1} 10%,{a1} 90%,transparent);
  transform:translateY(-50%) rotate(-3deg);box-shadow:0 0 20px {a1}cc}}
.sub{{font-family:Arial Black,sans-serif;font-size:46px;font-weight:900;
  color:{a1};letter-spacing:5px;margin-top:14px;border-top:4px solid {a1};
  padding-top:14px;text-shadow:0 0 15px {a1}99}}
.right{{position:absolute;right:0;top:0;width:640px;height:720px;
  display:flex;flex-direction:column;justify-content:center;
  align-items:flex-end;padding:40px 70px 40px 40px}}
.badge2{{display:inline-flex;background:linear-gradient(135deg,{a2},{a2}aa);
  padding:8px 22px;margin-bottom:20px}}
.badge2 span{{font-family:Arial Black,sans-serif;font-size:24px;font-weight:900;
  color:#000;letter-spacing:4px}}
.ev{{font-family:Arial Black,sans-serif;font-size:200px;font-weight:900;
  line-height:0.78;letter-spacing:-6px;text-align:right;color:{a2};
  text-shadow:0 0 60px {a2}dd,0 0 120px {a2}66,3px 3px 0 #003366}}
.proved{{font-family:Arial Black,sans-serif;font-size:38px;font-weight:900;
  color:#fff;letter-spacing:7px;text-align:right;margin-top:14px;
  border-top:4px solid {a2};padding-top:14px}}
.year{{font-family:Arial Black,sans-serif;font-size:60px;font-weight:900;
  color:{a2};text-align:right;letter-spacing:4px;text-shadow:0 0 30px {a2}}}
.light{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  font-size:110px;filter:drop-shadow(0 0 30px #ffff00) drop-shadow(0 0 60px #ff8800);z-index:20}}
.bottom{{position:absolute;bottom:0;left:0;right:0;height:72px;
  background:linear-gradient(90deg,rgba(180,0,0,0.95) 0%,rgba(0,0,0,0.98) 50%,rgba(0,60,150,0.95) 100%);
  border-top:3px solid rgba(255,255,255,0.15);display:flex;align-items:center;
  justify-content:space-between;padding:0 60px}}
.chn{{font-family:Arial Black,sans-serif;font-size:34px;font-weight:900;
  color:#fff;letter-spacing:8px;text-shadow:0 0 20px {a2}cc}}
.chn em{{color:{a2};font-style:normal}}
.ctag{{font-family:Arial,sans-serif;font-size:20px;font-weight:700;
  color:rgba(255,255,255,0.5);letter-spacing:4px}}
.c{{position:absolute;width:50px;height:50px}}
.tl{{top:18px;left:18px;border-top:5px solid {a1};border-left:5px solid {a1}}}
.tr{{top:18px;right:18px;border-top:5px solid {a2};border-right:5px solid {a2}}}
.bl{{bottom:80px;left:18px;border-bottom:5px solid {a1};border-left:5px solid {a1}}}
.br{{bottom:80px;right:18px;border-bottom:5px solid {a2};border-right:5px solid {a2}}}
</style></head><body>
<div class="wrap">
  <div class="gl"></div><div class="gr"></div>
  <div class="divider"></div>
  <div class="left">
    <div class="badge"><span>{ico} {lbl}</span></div>
    <div style="position:relative">
      <div class="t1">{l1}</div>
      <div class="t2">{l2}<div class="strike"></div></div>
    </div>
    <div class="sub">{l3}</div>
  </div>
  <div class="light">⚡</div>
  <div class="right">
    <div class="badge2"><span>EVCARIX ✓</span></div>
    <div class="ev">EV</div>
    <div class="proved">DATA INSIDE</div>
  </div>
  <div class="bottom">
    <div class="chn">⚡ <em>EV</em>CARIX</div>
    <div class="ctag">{lbl} & INSIGHTS</div>
  </div>
  <div class="c tl"></div><div class="c tr"></div>
  <div class="c bl"></div><div class="c br"></div>
</div></body></html>"""

    elif layout == "versus":
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;overflow:hidden;background:#000}}
.wrap{{width:1280px;height:720px;position:relative;overflow:hidden;
  background:linear-gradient(160deg,#000510 0%,#000 40%,#050010 100%)}}
.gl{{position:absolute;left:-100px;top:-100px;width:800px;height:800px;
  background:radial-gradient(circle,{g1} 0%,transparent 60%);filter:blur(30px)}}
.gr{{position:absolute;right:-100px;bottom:-100px;width:700px;height:700px;
  background:radial-gradient(circle,{g2} 0%,transparent 60%);filter:blur(30px)}}
.top{{position:absolute;top:0;left:0;right:0;height:80px;
  background:rgba(0,0,0,0.95);border-bottom:3px solid {a1};
  display:flex;align-items:center;padding:0 60px;gap:20px}}
.shock{{background:{a1};font-family:Arial Black,sans-serif;font-size:22px;
  font-weight:900;color:#fff;letter-spacing:4px;padding:6px 20px}}
.btxt{{font-family:Arial Black,sans-serif;font-size:26px;font-weight:900;
  color:rgba(255,255,255,0.5);letter-spacing:5px}}
.left{{position:absolute;left:0;top:80px;width:700px;height:570px;
  display:flex;flex-direction:column;justify-content:center;padding:30px 40px 30px 70px}}
.the{{font-family:Arial Black,sans-serif;font-size:36px;font-weight:900;
  color:rgba(255,255,255,0.4);letter-spacing:8px;margin-bottom:8px}}
.big{{font-family:Arial Black,sans-serif;font-size:140px;font-weight:900;
  line-height:0.82;letter-spacing:-4px;color:{a1};
  text-shadow:0 0 50px {a1}cc,0 0 100px {a1}55,4px 4px 0 #000}}
.big2{{font-family:Arial Black,sans-serif;font-size:68px;font-weight:900;
  color:#fff;letter-spacing:6px;margin-top:10px}}
.sub2{{margin-top:20px;padding-top:16px;border-top:4px solid {a1}88;
  font-family:Arial Black,sans-serif;font-size:28px;font-weight:900;
  color:{a2};letter-spacing:4px}}
.right{{position:absolute;right:0;top:80px;width:580px;height:570px;
  display:flex;flex-direction:column;justify-content:center;
  align-items:center;padding:30px 60px 30px 20px;gap:18px}}
.box{{width:100%;background:rgba(0,20,50,0.85);border-left:6px solid {a1};
  border-bottom:2px solid {a1}55;padding:16px 24px}}
.box.b2{{border-left-color:{a2};border-bottom-color:{a2}55}}
.box.b3{{border-left-color:#ffcc00;border-bottom-color:#ffcc0055}}
.bnum{{font-family:Arial Black,sans-serif;font-size:58px;font-weight:900;
  line-height:1;color:{a1};text-shadow:0 0 20px {a1}cc}}
.b2 .bnum{{color:{a2};text-shadow:0 0 20px {a2}cc}}
.b3 .bnum{{color:#ffcc00;text-shadow:0 0 20px #ffcc00cc}}
.blbl{{font-family:Arial,sans-serif;font-size:18px;font-weight:700;
  color:rgba(255,255,255,0.6);letter-spacing:3px;margin-top:2px}}
.vline{{position:absolute;left:700px;top:85px;bottom:78px;width:2px;
  background:linear-gradient(180deg,transparent,{a1} 20%,{a1}55 80%,transparent);filter:blur(1px)}}
.bottom{{position:absolute;bottom:0;left:0;right:0;height:72px;
  background:linear-gradient(90deg,rgba(0,10,30,0.98),rgba(0,20,60,0.98) 50%,rgba(0,10,30,0.98));
  border-top:3px solid {a1}66;display:flex;align-items:center;
  justify-content:space-between;padding:0 60px}}
.chn{{font-family:Arial Black,sans-serif;font-size:34px;font-weight:900;
  color:#fff;letter-spacing:8px;text-shadow:0 0 20px {a2}cc}}
.chn em{{color:{a2};font-style:normal}}
.ctag{{font-family:Arial,sans-serif;font-size:20px;font-weight:700;
  color:rgba(255,255,255,0.5);letter-spacing:4px}}
.c{{position:absolute;width:50px;height:50px}}
.tl{{top:85px;left:18px;border-top:5px solid {a1};border-left:5px solid {a1}}}
.tr{{top:85px;right:18px;border-top:5px solid {a2};border-right:5px solid {a2}}}
.bl{{bottom:78px;left:18px;border-bottom:5px solid {a1};border-left:5px solid {a1}}}
.br{{bottom:78px;right:18px;border-bottom:5px solid {a2};border-right:5px solid {a2}}}
</style></head><body>
<div class="wrap">
  <div class="gl"></div><div class="gr"></div>
  <div class="top">
    <div class="shock">🔥 SHOCKING</div>
    <div class="btxt">GAS CAR OWNERS MUST SEE THIS</div>
  </div>
  <div class="left">
    <div class="the">THE</div>
    <div class="big">{l1}<br>{l2}</div>
    <div class="sub2">😱 {l3}</div>
  </div>
  <div class="right">
    <div class="box"><div class="bnum">+300%</div><div class="blbl">EV SALES GROWTH</div></div>
    <div class="box b2"><div class="bnum">$0</div><div class="blbl">GAS CAR FUTURE VALUE</div></div>
    <div class="box b3"><div class="bnum">500MI</div><div class="blbl">NEW EV RANGE RECORD</div></div>
  </div>
  <div class="vline"></div>
  <div class="bottom">
    <div class="chn">⚡ <em>EV</em>CARIX</div>
    <div class="ctag">{lbl} & INSIGHTS</div>
  </div>
  <div class="c tl"></div><div class="c tr"></div>
  <div class="c bl"></div><div class="c br"></div>
</div></body></html>"""

    elif layout == "shock":
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;overflow:hidden;background:#000}}
.wrap{{width:1280px;height:720px;position:relative;overflow:hidden}}
.bg{{position:absolute;inset:0;
  background:radial-gradient(ellipse 80% 80% at 50% 50%,{style['left_bg']} 0%,#000 100%)}}
.glow_c{{position:absolute;left:50%;top:40%;transform:translate(-50%,-50%);
  width:900px;height:900px;
  background:radial-gradient(circle,{g1} 0%,{g2} 40%,transparent 70%);
  filter:blur(40px)}}
.stripe{{position:absolute;top:0;left:0;width:10px;height:100%;background:{a1}}}
.stripe2{{position:absolute;top:0;right:0;width:10px;height:100%;background:{a2}}}
.center{{position:absolute;inset:0;display:flex;flex-direction:column;
  justify-content:center;align-items:center;padding:20px 80px 80px}}
.ico_big{{font-size:100px;margin-bottom:10px;
  filter:drop-shadow(0 0 30px {a1}) drop-shadow(0 0 60px {a2})}}
.t1{{font-family:Arial Black,sans-serif;font-size:160px;font-weight:900;
  line-height:0.8;letter-spacing:-5px;color:{a1};text-align:center;
  text-shadow:0 0 60px {a1}cc,0 0 120px {a1}55,5px 5px 0 #000}}
.t2{{font-family:Arial Black,sans-serif;font-size:100px;font-weight:900;
  line-height:0.9;letter-spacing:-2px;color:#fff;text-align:center;
  text-shadow:0 0 30px {a2}88,4px 4px 0 #000;margin-top:10px}}
.t3{{font-family:Arial Black,sans-serif;font-size:60px;font-weight:900;
  color:{a2};text-align:center;letter-spacing:6px;margin-top:16px;
  text-shadow:0 0 20px {a2}cc}}
.bottom{{position:absolute;bottom:0;left:0;right:0;height:72px;
  background:rgba(0,0,0,0.95);border-top:3px solid {a1}88;
  display:flex;align-items:center;justify-content:space-between;padding:0 60px}}
.chn{{font-family:Arial Black,sans-serif;font-size:34px;font-weight:900;
  color:#fff;letter-spacing:8px;text-shadow:0 0 20px {a2}cc}}
.chn em{{color:{a2};font-style:normal}}
.ctag{{font-family:Arial,sans-serif;font-size:20px;font-weight:700;
  color:rgba(255,255,255,0.5);letter-spacing:4px}}
.c{{position:absolute;width:50px;height:50px}}
.tl{{top:18px;left:18px;border-top:5px solid {a1};border-left:5px solid {a1}}}
.tr{{top:18px;right:18px;border-top:5px solid {a2};border-right:5px solid {a2}}}
.bl{{bottom:80px;left:18px;border-bottom:5px solid {a1};border-left:5px solid {a1}}}
.br{{bottom:80px;right:18px;border-bottom:5px solid {a2};border-right:5px solid {a2}}}
</style></head><body>
<div class="wrap">
  <div class="bg"></div><div class="glow_c"></div>
  <div class="stripe"></div><div class="stripe2"></div>
  <div class="center">
    <div class="ico_big">{ico}</div>
    <div class="t1">{l1}</div>
    <div class="t2">{l2}</div>
    <div class="t3">{l3}</div>
  </div>
  <div class="bottom">
    <div class="chn">⚡ <em>EV</em>CARIX</div>
    <div class="ctag">{lbl} & INSIGHTS</div>
  </div>
  <div class="c tl"></div><div class="c tr"></div>
  <div class="c bl"></div><div class="c br"></div>
</div></body></html>"""

    else:  # data layout
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1280px;height:720px;overflow:hidden;background:#000}}
.wrap{{width:1280px;height:720px;position:relative;overflow:hidden;
  background:linear-gradient(135deg,{style['left_bg']} 0%,#000 50%,{style['right_bg']} 100%)}}
.gl{{position:absolute;left:-50px;top:-50px;width:600px;height:600px;
  background:radial-gradient(circle,{g1} 0%,transparent 65%);filter:blur(25px)}}
.gr{{position:absolute;right:-50px;bottom:-50px;width:600px;height:600px;
  background:radial-gradient(circle,{g2} 0%,transparent 65%);filter:blur(25px)}}
.left_bar{{position:absolute;left:0;top:0;width:8px;height:100%;background:{a1}}}
.header{{position:absolute;top:30px;left:40px;right:40px;
  display:flex;align-items:center;justify-content:space-between}}
.htag{{background:{a1};font-family:Arial Black,sans-serif;font-size:22px;
  font-weight:900;color:#fff;letter-spacing:4px;padding:8px 22px}}
.hico{{font-size:60px;filter:drop-shadow(0 0 15px {a1})}}
.main{{position:absolute;left:40px;top:120px;right:40px}}
.t1{{font-family:Arial Black,sans-serif;font-size:130px;font-weight:900;
  line-height:0.85;letter-spacing:-4px;color:{a1};
  text-shadow:0 0 50px {a1}bb,4px 4px 0 #000}}
.t2{{font-family:Arial Black,sans-serif;font-size:100px;font-weight:900;
  line-height:0.85;letter-spacing:-2px;color:#fff;
  text-shadow:0 0 20px {a1}55,3px 3px 0 #000;margin-top:8px}}
.t3{{font-family:Arial Black,sans-serif;font-size:56px;font-weight:900;
  color:{a2};letter-spacing:5px;margin-top:16px;
  border-left:6px solid {a2};padding-left:20px}}
.stats{{position:absolute;bottom:82px;left:40px;right:40px;
  display:flex;gap:20px}}
.st{{flex:1;background:rgba(0,0,0,0.75);border-top:4px solid {a1};padding:14px 18px}}
.st.s2{{border-top-color:{a2}}}
.st.s3{{border-top-color:#ffcc00}}
.sn{{font-family:Arial Black,sans-serif;font-size:42px;font-weight:900;
  color:{a1};text-shadow:0 0 15px {a1}cc}}
.s2 .sn{{color:{a2};text-shadow:0 0 15px {a2}cc}}
.s3 .sn{{color:#ffcc00;text-shadow:0 0 15px #ffcc00cc}}
.sl{{font-family:Arial,sans-serif;font-size:15px;font-weight:700;
  color:rgba(255,255,255,0.55);letter-spacing:2px;margin-top:4px}}
.bottom{{position:absolute;bottom:0;left:0;right:0;height:70px;
  background:rgba(0,0,0,0.96);border-top:2px solid {a1}55;
  display:flex;align-items:center;justify-content:space-between;padding:0 50px}}
.chn{{font-family:Arial Black,sans-serif;font-size:32px;font-weight:900;
  color:#fff;letter-spacing:7px;text-shadow:0 0 20px {a2}cc}}
.chn em{{color:{a2};font-style:normal}}
.ctag{{font-family:Arial,sans-serif;font-size:18px;font-weight:700;
  color:rgba(255,255,255,0.45);letter-spacing:3px}}
.c{{position:absolute;width:45px;height:45px}}
.tl{{top:15px;left:15px;border-top:5px solid {a1};border-left:5px solid {a1}}}
.tr{{top:15px;right:15px;border-top:5px solid {a2};border-right:5px solid {a2}}}
.bl{{bottom:78px;left:15px;border-bottom:5px solid {a1};border-left:5px solid {a1}}}
.br{{bottom:78px;right:15px;border-bottom:5px solid {a2};border-right:5px solid {a2}}}
</style></head><body>
<div class="wrap">
  <div class="gl"></div><div class="gr"></div>
  <div class="left_bar"></div>
  <div class="header">
    <div class="htag">{ico} {lbl}</div>
    <div class="hico">{ico}</div>
  </div>
  <div class="main">
    <div class="t1">{l1}</div>
    <div class="t2">{l2}</div>
    <div class="t3">{l3}</div>
  </div>
  <div class="stats">
    <div class="st"><div class="sn">2026</div><div class="sl">REAL DATA</div></div>
    <div class="st s2"><div class="sn">HD</div><div class="sl">QUALITY</div></div>
    <div class="st s3"><div class="sn">FACTS</div><div class="sl">BACKED</div></div>
  </div>
  <div class="bottom">
    <div class="chn">⚡ <em>EV</em>CARIX</div>
    <div class="ctag">{lbl} & INSIGHTS</div>
  </div>
  <div class="c tl"></div><div class="c tr"></div>
  <div class="c bl"></div><div class="c br"></div>
</div></body></html>"""


class ThumbnailGenerator:

    def create(self, title: str, topic: str) -> str:
        try:
            layout   = random.choice(LAYOUTS)
            html     = _build_html(title, topic, layout)

            safe_t   = re.sub(r"[^\w]", "_", title[:30])
            out_path = os.path.join(OUTPUT_DIR, f"thumb_{safe_t}_{layout}.jpg")

            with tempfile.NamedTemporaryFile(suffix=".html", delete=False,
                                             mode="w", encoding="utf-8") as f:
                f.write(html)
                tmp_html = f.name

            cmd = [
                "wkhtmltoimage",
                "--width",  "1280",
                "--height", "720",
                "--quality", "95",
                "--zoom", "1",
                "--disable-smart-width",
                tmp_html,
                out_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            os.unlink(tmp_html)

            if result.returncode == 0 and os.path.exists(out_path):
                size = os.path.getsize(out_path)
                print(f"[Thumbnail] ✅ {layout} layout — {size//1024}KB → {out_path}")
                return out_path
            else:
                print(f"[Thumbnail] ❌ wkhtmltoimage failed: {result.stderr[-200:]}")
                return None

        except Exception as e:
            print(f"[Thumbnail] ❌ create() error: {e}")
            return None

    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        try:
            token_json  = os.getenv("YOUTUBE_TOKEN_JSON")
            secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")

            if not token_json or not secret_json:
                print("[Thumbnail] Missing YouTube credentials")
                return False

            token_data  = json.loads(token_json)
            secret_data = json.loads(secret_json)
            client_id   = secret_data["installed"]["client_id"]
            client_sec  = secret_data["installed"]["client_secret"]

            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_sec,
                scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
            )

            youtube = build("youtube", "v3", credentials=creds)
            media   = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()

            print(f"[Thumbnail] ✅ YouTube'a yüklendi: {video_id}")
            return True

        except Exception as e:
            print(f"[Thumbnail] ❌ Upload failed: {e}")
            return False


def generate_and_upload(video_id: str, title: str, topic: str) -> bool:
    gen  = ThumbnailGenerator()
    path = gen.create(title, topic)
    if path and os.path.exists(path):
        return gen.upload_thumbnail(video_id, path)
    return False
