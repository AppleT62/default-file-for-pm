#!/usr/bin/env python3
"""easy-report/*.md 13장 → 단일 웹 보고서 HTML 생성."""
import re, html, glob, os, json

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

FILES = ['01-BEGIN','02-CLOUD','03-LAYERS','04-TIME','05-FREEDOM','06-AMORFATI',
         '07-RELATIONS','08-APPENDIX','09-EMOTION','10-TRIAL','11-OPEN',
         '12-PROTOCOL','13-METHOD']

# ---------- inline ----------
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', t)
    # 신념도 수치를 계기 표기로
    t = re.sub(r'(?<![\d>])(\d{1,3})%', r'<span class="pct">\1%</span>', t)
    return t

VERDICT = {'확인됨':'ok','유망함':'mid','실존적 유망':'mid','정합':'mid',
           '차용':'borrow','은유':'meta','불성립':'no'}
def chip(txt):
    cls = 'mid'
    for k,v in VERDICT.items():
        if txt.startswith(k) or k in txt[:6]:
            cls = v; break
    if txt.startswith('❌') or '불성립' in txt: cls='no'
    elif txt.startswith('✅') or '확인됨' in txt: cls='ok'
    elif txt.startswith('🔶') or '차용' in txt: cls='borrow'
    elif txt.startswith('〰️') or '은유' in txt: cls='meta'
    clean = re.sub(r'^[✅🟡🔶〰️❌]️?\s*','',txt)
    return f'<span class="chip {cls}">{inline(clean)}</span>'

# ---------- block ----------
def render(md, idx):
    md = re.sub(r'<!--[\s\S]*?-->', '', md)
    lines = md.split('\n')
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1; continue
        # fenced code block → 도식(diagram) 블록
        if s.startswith('```'):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(html.escape(lines[i].rstrip(), quote=False)); i += 1
            i += 1
            out.append('<pre class="diagram">' + '\n'.join(buf) + '</pre>')
            continue
        # table
        if s.startswith('|') and i+1 < n and re.match(r'^\|[\s:|-]+\|$', lines[i+1].strip()):
            head = [c.strip() for c in s.strip('|').split('|')]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            th = ''.join(f'<th>{inline(c)}</th>' for c in head)
            body = []
            verdict_col = len(head)-1 if any('판정' in c for c in head) else -1
            for r in rows:
                tds = []
                for ci, c in enumerate(r):
                    if ci == verdict_col and c:
                        cells = ' '.join(chip(x.strip()) for x in c.split(' / '))
                        tds.append(f'<td class="v">{cells}</td>')
                    else:
                        tds.append(f'<td>{inline(c)}</td>')
                body.append('<tr>' + ''.join(tds) + '</tr>')
            out.append(f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')
            continue
        # hr
        if re.match(r'^-{3,}$', s):
            out.append('<hr>'); i += 1; continue
        # heading
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2)
            if lvl == 1:
                i += 1; continue          # 장 제목은 섹션 헤더에서 별도 출력
            tag = 'h3' if lvl == 2 else 'h4'
            out.append(f'<{tag}>{inline(txt)}</{tag}>')
            i += 1; continue
        # blockquote
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip()); i += 1
            txt = ' '.join(x for x in buf if x)
            txt = re.sub(r'\s*·\s*', ' · ', txt)
            out.append(f'<blockquote>{inline(txt)}</blockquote>')
            continue
        # list
        if re.match(r'^[-*]\s+', s):
            items = []
            while i < n and re.match(r'^[-*]\s+', lines[i].strip()):
                items.append(re.sub(r'^[-*]\s+', '', lines[i].strip())); i += 1
            li = ''.join(f'<li>{inline(x)}</li>' for x in items)
            out.append(f'<ul>{li}</ul>')
            continue
        if re.match(r'^\d+\.\s+', s):
            items = []
            while i < n and re.match(r'^\d+\.\s+', lines[i].strip()):
                items.append(re.sub(r'^\d+\.\s+', '', lines[i].strip())); i += 1
            li = ''.join(f'<li>{inline(x)}</li>' for x in items)
            out.append(f'<ol>{li}</ol>')
            continue
        # paragraph (연속 줄 병합)
        buf = []
        while i < n and lines[i].strip() and not re.match(r'^(#{1,4}\s|[-*]\s|\d+\.\s|>|\||-{3,}$)', lines[i].strip()):
            buf.append(lines[i].strip()); i += 1
        p = ' '.join(buf)
        cls = ' class="note"' if p.startswith('*(') or p.startswith('<em>(') else ''
        out.append(f'<p{cls}>{inline(p)}</p>')
    return '\n'.join(out)

chapters = []
for k, stem in enumerate(FILES):
    raw = open(os.path.join(SRC, stem + '.md'), encoding='utf-8').read()
    m = re.search(r'^# (.+)$', raw, re.M)
    full = m.group(1).strip()
    if k == 0:
        num, label = '0', '프롤로그'
        title = full.replace('프롤로그 — ', '')
    else:
        mm = re.match(r'^(\d+)장 — (.+)$', full)
        num, title = mm.group(1), mm.group(2)
        label = f'{num}장'
    chapters.append({'id': f'ch{k}', 'num': num, 'label': label,
                     'title': title, 'full': full, 'body': render(raw, k)})

nav = '\n'.join(
    f'<li><a href="#{c["id"]}" data-t="{c["id"]}">'
    f'<span class="n">{c["num"]}</span><span class="t">{html.escape(c["title"])}</span></a></li>'
    for c in chapters)

secs = []
for c in chapters:
    star = '<span class="star" aria-hidden="true">★</span>' if '★' in c['full'] else ''
    t = c['title'].replace(' ★','')
    secs.append(f'''<section id="{c['id']}" class="ch">
<header class="ch-h"><p class="ch-n">{c['label']}</p><h2>{html.escape(t)}{star}</h2></header>
{c['body']}
</section>''')

HTML = f'''<title>미래는 가중되어 있다 — 쉬운말 보고서</title>
<style>
:root {{
  --bg:#EDEFF1; --surface:#F8F9FA; --raise:#FFFFFF;
  --text:#141A20; --muted:#5A6673; --faint:#8695A3;
  --line:#D3D8DD; --hair:#E3E7EA;
  --accent:#8C5F16; --accent-soft:#F0E4CE;
  --ok:#2C6A4B; --mid:#8A6A1C; --no:#8C3A32; --meta:#6B7681; --borrow:#7A5230;
  --serif:"Nanum Myeongjo","Apple Myungjo",AppleMyungjo,Batang,"Source Serif 4",Georgia,serif;
  --sans:Pretendard,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono","JetBrains Mono","Menlo",monospace;
}}
@media (prefers-color-scheme:dark) {{
  :root {{
    --bg:#0E1216; --surface:#141A20; --raise:#19212A;
    --text:#DFE5EB; --muted:#93A0AD; --faint:#6D7B89;
    --line:#242D36; --hair:#1D242C;
    --accent:#D6A047; --accent-soft:#2A2317;
    --ok:#6BB48C; --mid:#C9A75C; --no:#D98079; --meta:#8B96A1; --borrow:#C39A6B;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#0E1216; --surface:#141A20; --raise:#19212A;
  --text:#DFE5EB; --muted:#93A0AD; --faint:#6D7B89;
  --line:#242D36; --hair:#1D242C;
  --accent:#D6A047; --accent-soft:#2A2317;
  --ok:#6BB48C; --mid:#C9A75C; --no:#D98079; --meta:#8B96A1; --borrow:#C39A6B;
}}
:root[data-theme="light"] {{
  --bg:#EDEFF1; --surface:#F8F9FA; --raise:#FFFFFF;
  --text:#141A20; --muted:#5A6673; --faint:#8695A3;
  --line:#D3D8DD; --hair:#E3E7EA;
  --accent:#8C5F16; --accent-soft:#F0E4CE;
  --ok:#2C6A4B; --mid:#8A6A1C; --no:#8C3A32; --meta:#6B7681; --borrow:#7A5230;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text);
  font-family:var(--sans); font-size:17px; line-height:1.85;
  -webkit-font-smoothing:antialiased; word-break:keep-all; overflow-wrap:break-word; }}
#bar {{ position:fixed; top:0; left:0; height:2px; background:var(--accent); width:0; z-index:50; transition:width .1s linear; }}

/* layout */
.wrap {{ display:grid; grid-template-columns:250px minmax(0,1fr); gap:0; max-width:1180px; margin:0 auto; }}
nav.rail {{ position:sticky; top:0; height:100vh; overflow-y:auto; padding:34px 20px 40px 24px;
  border-right:1px solid var(--hair); }}
nav.rail .brand {{ font-family:var(--serif); font-size:15px; line-height:1.5; margin:0 0 4px; }}
nav.rail .meta {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.06em; color:var(--faint);
  text-transform:uppercase; margin:0 0 22px; }}
nav.rail ol {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:1px; }}
nav.rail a {{ display:grid; grid-template-columns:26px 1fr; gap:8px; align-items:baseline;
  padding:6px 8px 6px 6px; border-radius:3px; text-decoration:none; color:var(--muted);
  font-size:13.5px; line-height:1.45; border-left:2px solid transparent; }}
nav.rail a .n {{ font-family:var(--mono); font-size:11px; color:var(--faint); font-variant-numeric:tabular-nums; }}
nav.rail a:hover {{ color:var(--text); background:var(--surface); }}
nav.rail a.on {{ color:var(--text); border-left-color:var(--accent); background:var(--surface); }}
nav.rail a.on .n {{ color:var(--accent); }}
nav.rail a:focus-visible {{ outline:2px solid var(--accent); outline-offset:1px; }}

main {{ padding:0 44px 120px; min-width:0; }}

/* hero */
.hero {{ padding:96px 0 60px; border-bottom:1px solid var(--hair); }}
.eyebrow {{ font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--accent); margin:0 0 20px; }}
.hero h1 {{ font-family:var(--serif); font-weight:400; font-size:clamp(30px,4.4vw,50px);
  line-height:1.32; letter-spacing:-.01em; margin:0 0 26px; text-wrap:balance; }}
.hero h1 em {{ font-style:normal; color:var(--accent); }}
.lede {{ font-size:17.5px; color:var(--muted); max-width:60ch; margin:0 0 34px; }}
#curve {{ width:100%; height:132px; display:block; margin:0 0 30px; }}
.facts {{ display:flex; flex-wrap:wrap; gap:0; border-top:1px solid var(--hair); }}
.fact {{ flex:1 1 130px; padding:14px 16px 14px 0; }}
.fact b {{ display:block; font-family:var(--mono); font-size:20px; font-variant-numeric:tabular-nums;
  font-weight:600; color:var(--text); line-height:1.2; }}
.fact span {{ font-size:11.5px; color:var(--faint); letter-spacing:.02em; }}

/* chapter */
.ch {{ padding:74px 0 10px; scroll-margin-top:20px; }}
.ch + .ch {{ border-top:1px solid var(--hair); }}
.ch-h {{ margin:0 0 34px; }}
.ch-n {{ font-family:var(--mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0 0 10px; }}
.ch h2 {{ font-family:var(--serif); font-weight:400; font-size:clamp(24px,3.1vw,34px); line-height:1.35;
  margin:0; letter-spacing:-.005em; text-wrap:balance; }}
.star {{ color:var(--accent); font-size:.62em; vertical-align:.35em; margin-left:.3em; }}
.ch h3 {{ font-family:var(--sans); font-weight:700; font-size:19px; line-height:1.5;
  margin:52px 0 14px; letter-spacing:-.005em; }}
.ch h4 {{ font-family:var(--sans); font-weight:700; font-size:16px; color:var(--muted);
  margin:34px 0 10px; }}
.ch p {{ margin:0 0 19px; max-width:66ch; }}
.ch p.note {{ font-size:15px; color:var(--muted); border-left:2px solid var(--line);
  padding-left:15px; margin:22px 0; }}
.ch ul, .ch ol {{ max-width:66ch; margin:0 0 22px; padding-left:20px; }}
.ch li {{ margin:0 0 9px; }}
.ch li::marker {{ color:var(--faint); }}
blockquote {{ margin:30px 0; padding:20px 0 20px 24px; border-left:2px solid var(--accent);
  font-family:var(--serif); font-size:19.5px; line-height:1.72; max-width:60ch; }}
blockquote strong {{ font-weight:700; }}
code {{ font-family:var(--mono); font-size:.85em; background:var(--surface);
  border:1px solid var(--hair); border-radius:3px; padding:.1em .34em; }}
strong {{ font-weight:700; }}
.pct {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:.93em;
  color:var(--accent); font-weight:600; }}
hr {{ border:0; border-top:1px solid var(--hair); margin:44px 0; max-width:66ch; }}
pre.diagram {{ font-family:var(--mono); font-size:13px; line-height:1.95; margin:26px 0 30px;
  padding:20px 22px; background:var(--surface); border:1px solid var(--hair); border-left:2px solid var(--accent);
  border-radius:4px; overflow-x:auto; color:var(--muted); max-width:66ch; }}

/* table */
.tw {{ overflow-x:auto; margin:28px 0 34px; border:1px solid var(--hair); border-radius:4px;
  background:var(--surface); }}
table {{ border-collapse:collapse; width:100%; font-size:14px; min-width:560px; }}
th {{ text-align:left; font-family:var(--mono); font-size:10.5px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--faint); font-weight:500;
  padding:11px 14px; border-bottom:1px solid var(--line); white-space:nowrap; }}
td {{ padding:11px 14px; border-bottom:1px solid var(--hair); vertical-align:top; line-height:1.65; }}
tbody tr:last-child td {{ border-bottom:0; }}
td:first-child {{ font-family:var(--mono); font-variant-numeric:tabular-nums; color:var(--faint);
  white-space:nowrap; font-size:12.5px; }}
td.v {{ white-space:nowrap; }}
.chip {{ display:inline-block; font-size:11.5px; line-height:1.6; padding:1px 8px; border-radius:99px;
  border:1px solid currentColor; margin:1px 3px 1px 0; white-space:nowrap; }}
.chip.ok {{ color:var(--ok); }} .chip.mid {{ color:var(--mid); }} .chip.no {{ color:var(--no); }}
.chip.meta {{ color:var(--meta); }} .chip.borrow {{ color:var(--borrow); }}

footer {{ max-width:66ch; margin:80px 0 0; padding-top:26px; border-top:1px solid var(--hair);
  font-size:13.5px; color:var(--faint); line-height:1.75; }}
footer code {{ font-size:12px; }}

/* mobile */
.mnav {{ display:none; }}
@media (max-width:900px) {{
  .wrap {{ grid-template-columns:1fr; }}
  nav.rail {{ display:none; }}
  main {{ padding:0 22px 90px; }}
  .hero {{ padding:70px 0 46px; }}
  .mnav {{ display:block; position:sticky; top:0; z-index:20; background:var(--bg);
    border-bottom:1px solid var(--hair); padding:9px 0; margin:0 0 0; }}
  .mnav select {{ width:100%; font-family:var(--sans); font-size:14px; padding:9px 10px;
    background:var(--surface); color:var(--text); border:1px solid var(--line); border-radius:4px; }}
  body {{ font-size:16.5px; }}
}}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; animation:none !important; }} }}
</style>

<div id="bar"></div>
<div class="wrap">
<nav class="rail" aria-label="목차">
  <p class="brand">미래는 가중되어 있다</p>
  <p class="meta">쉬운말 보고서 · 회차 84</p>
  <ol>{nav}</ol>
</nav>
<main>
  <div class="mnav"><select id="msel" aria-label="장 이동">{ ''.join(f'<option value="{c["id"]}">{c["label"]} · {html.escape(c["title"])[:24]}</option>' for c in chapters) }</select></div>

  <div class="hero">
    <p class="eyebrow">시간 · 차원 · 운명 검증 루프 — 쉬운말 완역본</p>
    <h1>미래는 열려 있지도, 닫혀 있지도 않다.<br><em>미래는 기울어져 있다.</em></h1>
    <p class="lede">84회차의 자기 검증을 거친 세계관 보고서를, 철학을 몰라도 읽을 수 있게 옮긴 판본입니다. 내용을 빼거나 부드럽게 만들지 않았습니다 — 확신도 수치도, 스스로 틀렸다고 인정한 기록도 그대로입니다.</p>
    <canvas id="curve" aria-label="한쪽으로 기울어진 확률 분포 곡선" role="img"></canvas>
    <div class="facts">
      <div class="fact"><b>84</b><span>검증 회차</span></div>
      <div class="fact"><b>30</b><span>외부 판정 위임</span></div>
      <div class="fact"><b>44</b><span>검토한 연결</span></div>
      <div class="fact"><b>7</b><span>시험 전 예측</span></div>
      <div class="fact"><b>17</b><span>아직 열린 문제</span></div>
    </div>
  </div>

{''.join(secs)}

  <footer>
    원천: <code>index.html</code>(대시보드 보고서, 회차 84) → <code>easy-report/</code> 쉬운말 완역본 13장.
    무손실·무변형·이해 순서 재배치 3원칙으로 옮겼으며, 원문 35개 섹션 전건이 매핑 검증을 통과했습니다.
    신념도 수치는 측정값이 아니라 정직한 자기 평가이며, 근거가 약해질 때마다 내려간 이력이 함께 기록돼 있습니다.
  </footer>
</main>
</div>

<script>
// 기울어진 분포 곡선
(function () {{
  const cv = document.getElementById('curve');
  const rm = matchMedia('(prefers-reduced-motion:reduce)').matches;
  function draw(p) {{
    const r = devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
    cv.width = w * r; cv.height = h * r;
    const c = cv.getContext('2d'); c.setTransform(r, 0, 0, r, 0, 0); c.clearRect(0, 0, w, h);
    const cs = getComputedStyle(document.documentElement);
    const acc = cs.getPropertyValue('--accent').trim();
    const line = cs.getPropertyValue('--line').trim();
    const faint = cs.getPropertyValue('--faint').trim();
    const pad = 2, base = h - 20;
    // 축
    c.strokeStyle = line; c.lineWidth = 1;
    c.beginPath(); c.moveTo(0, base + .5); c.lineTo(w, base + .5); c.stroke();
    // 기울어진(대수정규) 분포
    const f = x => {{ const t = x / w * 3.4 + .05;
      return Math.exp(-Math.pow(Math.log(t) + .12, 2) / 0.42) / (t * 1.35); }};
    let mx = 0; for (let x = 0; x <= w; x++) mx = Math.max(mx, f(x));
    const end = Math.max(2, Math.floor(w * p));
    const pt = x => base - (f(x) / mx) * (base - pad) * .94;
    // 면
    const g = c.createLinearGradient(0, 0, 0, base);
    g.addColorStop(0, acc + '38'); g.addColorStop(1, acc + '05');
    c.beginPath(); c.moveTo(0, base);
    for (let x = 0; x <= end; x++) c.lineTo(x, pt(x));
    c.lineTo(end, base); c.closePath(); c.fillStyle = g; c.fill();
    // 선
    c.beginPath(); c.moveTo(0, pt(0));
    for (let x = 1; x <= end; x++) c.lineTo(x, pt(x));
    c.strokeStyle = acc; c.lineWidth = 1.6; c.stroke();
    // 최빈값 눈금
    let px = 0, pv = 0; for (let x = 0; x <= w; x++) {{ const v = f(x); if (v > pv) {{ pv = v; px = x; }} }}
    if (end > px) {{
      c.setLineDash([2, 3]); c.strokeStyle = faint; c.lineWidth = 1;
      c.beginPath(); c.moveTo(px + .5, pt(px)); c.lineTo(px + .5, base); c.stroke(); c.setLineDash([]);
      c.fillStyle = acc; c.beginPath(); c.arc(px, pt(px), 2.6, 0, 7); c.fill();
    }}
  }}
  let t0 = null;
  function run(ts) {{ if (!t0) t0 = ts; const p = Math.min(1, (ts - t0) / 900);
    draw(p < 1 ? 1 - Math.pow(1 - p, 3) : 1); if (p < 1) requestAnimationFrame(run); }}
  if (rm) draw(1); else requestAnimationFrame(run);
  addEventListener('resize', () => draw(1));
  matchMedia('(prefers-color-scheme:dark)').addEventListener('change', () => draw(1));
  new MutationObserver(() => draw(1)).observe(document.documentElement, {{ attributes:true, attributeFilter:['data-theme'] }});
}})();

// 읽기 진행바 + 목차 활성
(function () {{
  const bar = document.getElementById('bar');
  addEventListener('scroll', () => {{
    const m = document.documentElement.scrollHeight - innerHeight;
    bar.style.width = (m > 0 ? scrollY / m * 100 : 0) + '%';
  }}, {{ passive:true }});
  const links = [...document.querySelectorAll('nav.rail a')];
  const map = Object.fromEntries(links.map(a => [a.dataset.t, a]));
  const io = new IntersectionObserver(es => {{
    es.forEach(e => {{ if (e.isIntersecting) {{
      links.forEach(a => a.classList.remove('on'));
      const a = map[e.target.id]; if (a) {{ a.classList.add('on');
        const r = a.getBoundingClientRect(); if (r.top < 60 || r.bottom > innerHeight - 40)
          a.scrollIntoView({{ block:'center' }}); }}
    }} }});
  }}, {{ rootMargin:'-15% 0px -75% 0px' }});
  document.querySelectorAll('section.ch').forEach(s => io.observe(s));
  const sel = document.getElementById('msel');
  if (sel) sel.addEventListener('change', e =>
    document.getElementById(e.target.value).scrollIntoView({{ behavior:'smooth' }}));
}})();
</script>'''

open(OUT, 'w', encoding='utf-8').write(HTML)
print('wrote', OUT, len(HTML), 'chars ·', len(chapters), 'chapters')
