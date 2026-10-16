"""Build the blog from posts-src/*.txt.

Each post file is a few `key: value` header lines (title, date, tag, icon,
summary), a `---` line, then the body. The body supports paragraphs, `## `
headings, `- ` bullet lists and [links](https://...). Run `python build_blog.py`
after adding or editing a post; it rewrites blog/ and the "From the blog"
strip on the homepage.
"""
import datetime
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "posts-src"
OUT = ROOT / "blog"
HOME = ROOT / "index.html"
WPM = 220


def parse(path):
    head, body = path.read_text(encoding="utf-8").split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    meta["slug"] = re.sub(r"^\d+-", "", path.stem)
    meta["body"] = body.strip()
    meta["words"] = len(body.split())
    meta["minutes"] = max(1, round(meta["words"] / WPM))
    d = datetime.date.fromisoformat(meta["date"])
    meta["pretty"] = d.strftime("%B %d, %Y").replace(" 0", " ")
    return meta


def inline(text):
    text = html.escape(text, quote=False)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m[2])}" rel="noopener">{m[1]}</a>', text)


def render_body(body):
    out = []
    for block in re.split(r"\n\s*\n", body):
        lines = block.strip().splitlines()
        if lines[0].startswith("## "):
            title = lines[0][3:]
            anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            out.append(f'<h2 id="{anchor}">{inline(title)}</h2>')
            lines = lines[1:]
            if not lines:
                continue
        if all(l.startswith("- ") for l in lines):
            out.append("<ul>" + "".join(f"<li>{inline(l[2:])}</li>" for l in lines) + "</ul>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


STYLE = """
  :root { --bg:#020604; --panel:#0b120d; --line:#18261b; --text:#cfd8cc; --muted:#7f8c7c; --green:#6dff8a; --green-dim:#2c7a3c; --stamp:#b3261e; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:17px/1.75 "IBM Plex Sans", system-ui, sans-serif; overflow-x:hidden; }
  ::selection { background:var(--green); color:#000; }
  a { color:var(--green); }
  .wrap { max-width:1120px; margin:0 auto; padding:0 16px; }
  nav { position:sticky; top:0; z-index:40; background:rgba(2,6,4,.9); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }
  nav .wrap { display:flex; gap:22px; align-items:center; height:56px; overflow-x:auto; scrollbar-width:none; }
  nav .brand { font-family:"VT323", monospace; font-size:24px; color:var(--green); text-decoration:none; white-space:nowrap; text-shadow:0 0 10px rgba(109,255,138,.5); }
  nav a.link { color:var(--muted); text-decoration:none; font-size:14px; white-space:nowrap; }
  nav a.link:hover, nav a.link.here { color:var(--green); }
  #progress { position:fixed; top:0; left:0; height:3px; width:0; background:var(--green); box-shadow:0 0 12px var(--green); z-index:60; }
  .masthead { position:relative; overflow:hidden; border-bottom:1px solid var(--line); background:radial-gradient(ellipse at 50% 120%, #0d3018, var(--bg) 70%); }
  .masthead canvas { position:absolute; inset:0; width:100%; height:100%; }
  .masthead .wrap { position:relative; padding-top:90px; padding-bottom:70px; }
  .kicker { font-family:"VT323", monospace; color:var(--green); font-size:20px; letter-spacing:.14em; }
  h1 { font-family:"Special Elite", cursive; font-weight:normal; font-size:clamp(34px, 6.5vw, 64px); line-height:1.08; margin:.15em 0 .3em; color:#eef7ec; text-shadow:0 0 30px rgba(109,255,138,.2); }
  .meta { color:var(--muted); font-size:14px; display:flex; flex-wrap:wrap; gap:6px 18px; }
  .meta b { color:var(--green); font-weight:normal; font-family:"VT323", monospace; font-size:18px; }
  .stamp { display:inline-block; border:3px double var(--stamp); color:var(--stamp); font-family:"Special Elite", cursive; padding:2px 10px; letter-spacing:.12em; transform:rotate(-6deg); margin-top:18px; opacity:.85; }
  article.post { max-width:700px; margin:0 auto; padding:56px 16px 40px; }
  article.post .lede { font-size:20px; color:#e3ebe0; margin-top:0; }
  article.post h2 { font-family:"Special Elite", cursive; font-weight:normal; color:#eef7ec; font-size:28px; line-height:1.2; margin:44px 0 10px; }
  article.post h2::before { content:"// "; color:var(--green); font-family:"VT323", monospace; }
  article.post ul { padding-left:22px; } article.post li { margin:6px 0; } article.post li::marker { color:var(--green); }
  .pager { max-width:700px; margin:0 auto 90px; padding:0 16px; display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .pager a { display:block; border:1px solid var(--line); padding:16px 18px; text-decoration:none; color:var(--text); background:var(--panel); transition:border-color .2s, transform .2s; }
  .pager a:hover { border-color:var(--green-dim); transform:translateY(-2px); }
  .pager small { display:block; font-family:"VT323", monospace; color:var(--green); font-size:17px; }
  .pager .next { text-align:right; grid-column:2; }
  .tools { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:36px 0 26px; }
  .chip { background:transparent; border:1px solid var(--green-dim); color:var(--text); padding:6px 15px; font:14px "IBM Plex Sans", sans-serif; cursor:pointer; border-radius:999px; transition:.2s; }
  .chip:hover { border-color:var(--green); }
  .chip[aria-pressed="true"] { background:var(--green); color:#031; border-color:var(--green); font-weight:600; }
  .search { margin-left:auto; background:#010301; border:1px solid var(--line); color:var(--green); font:19px "VT323", monospace; padding:6px 12px; min-width:0; width:240px; max-width:100%; outline:0; }
  .search:focus { border-color:var(--green-dim); }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(310px, 1fr)); gap:18px; padding-bottom:100px; }
  .card { position:relative; display:flex; flex-direction:column; text-decoration:none; color:var(--text); background:linear-gradient(160deg, #0f1912, #070b08); border:1px solid var(--line); overflow:hidden; transition:transform .25s, border-color .25s, box-shadow .25s; }
  .card:hover { transform:translateY(-4px); border-color:#2a4a31; box-shadow:0 20px 40px rgba(0,0,0,.45), 0 0 30px rgba(109,255,138,.08); }
  .card .art { height:130px; display:grid; place-items:center; font-size:46px; position:relative; border-bottom:1px solid var(--line);
    background:radial-gradient(circle at 50% 120%, rgba(109,255,138,.22), transparent 60%), repeating-linear-gradient(0deg, rgba(109,255,138,.04) 0 1px, transparent 1px 4px), #050906; }
  .card .art span { filter:drop-shadow(0 0 18px rgba(109,255,138,.45)); transition:transform .4s; }
  .card:hover .art span { transform:scale(1.15) rotate(-4deg); }
  .card .num { position:absolute; top:10px; left:14px; font-family:"VT323", monospace; color:var(--green); font-size:18px; }
  .card .body { padding:18px 20px 20px; display:flex; flex-direction:column; flex:1; }
  .card h3 { font-family:"Special Elite", cursive; font-weight:normal; font-size:22px; line-height:1.2; margin:0 0 8px; color:#eef7ec; }
  .card p { margin:0 0 14px; color:var(--muted); font-size:15px; line-height:1.55; flex:1; }
  .card .foot { display:flex; justify-content:space-between; font-size:13px; color:var(--muted); }
  .card .foot b { color:var(--green); font-weight:normal; }
  .card[hidden] { display:none; }
  .empty { color:var(--muted); font-family:"VT323", monospace; font-size:22px; }
  footer { padding:50px 0 60px; border-top:1px solid var(--line); color:var(--muted); font-size:13px; text-align:center; }
  @media (max-width:640px) { body { font-size:16px; } .search { margin-left:0; width:100%; } .pager { grid-template-columns:1fr; } .pager .next { grid-column:1; } }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
"""

STARS = """
(() => {
  const c = document.getElementById('stars'); if (!c) return;
  const x = c.getContext('2d'), still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let w, h, s = [];
  function size() { const r = devicePixelRatio || 1; w = c.clientWidth; h = c.clientHeight; c.width = w * r; c.height = h * r; x.setTransform(r, 0, 0, r, 0, 0);
    s = Array.from({ length: Math.round(w * h / 1800) }, () => ({ x: Math.random() * w, y: Math.random() * h, r: Math.random() ** 3 * 1.6 + .3, p: Math.random() * 6, v: Math.random() * .08 + .02 })); }
  function draw(t) { x.clearRect(0, 0, w, h);
    for (const a of s) { a.x -= a.v; if (a.x < 0) a.x = w; x.globalAlpha = .35 + .65 * Math.abs(Math.sin(t / 1400 + a.p)); x.fillStyle = a.r > 1.2 ? '#bfffd0' : '#e8f5e5'; x.beginPath(); x.arc(a.x, a.y, a.r, 0, 7); x.fill(); }
    if (!still) requestAnimationFrame(draw); }
  addEventListener('resize', size); size(); requestAnimationFrame(draw);
  const k = document.querySelector('[data-decrypt]');
  if (k && !still) { const T = k.textContent, G = '!<>-_/[]{}=+*^?#ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'; let f = 0;
    const iv = setInterval(() => { const d = f++ >> 1; k.textContent = [...T].map((ch, i) => i < d || ch === ' ' ? ch : G[Math.random() * G.length | 0]).join(''); if (d >= T.length) clearInterval(iv); }, 40); }
})();
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#020604">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&family=VT323&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{style}</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brand" href="../">&gt; MULDER_ITS_ME</a>
  <a class="link" href="../#basement">The Office</a>
  <a class="link" href="../#board">Conspiracy</a>
  <a class="link" href="../#cases">Case Files</a>
  <a class="link here" href="./">Blog</a>
</div></nav>
"""

FOOT = """<footer><div class="wrap">
  <div class="kicker">THE TRUTH IS OUT THERE</div>
  <p>An unofficial, non-commercial fan page. Not affiliated with or endorsed by 20th Century Studios, Fox, or Ten Thirteen Productions.
  The X-Files and all related names are trademarks of their respective owners.</p>
</div></footer>
<script>{stars}</script>
{extra}
</body>
</html>
"""

PROGRESS = """<script>
(() => { const p = document.getElementById('progress'), a = document.querySelector('article.post');
  addEventListener('scroll', () => { const r = a.getBoundingClientRect(); const t = Math.min(1, Math.max(0, -r.top / (r.height - innerHeight)));
    p.style.width = t * 100 + '%'; }, { passive: true }); })();
</script>"""

INDEX_JS = """<script>
(() => {
  const cards = [...document.querySelectorAll('.card')], chips = document.querySelectorAll('.chip'), q = document.getElementById('q'), empty = document.getElementById('empty');
  let tag = 'all';
  function apply() { const term = q.value.trim().toLowerCase(); let n = 0;
    cards.forEach(c => { const ok = (tag === 'all' || c.dataset.tag === tag) && (!term || c.dataset.text.includes(term)); c.hidden = !ok; n += ok; });
    empty.hidden = n > 0; }
  chips.forEach(b => b.addEventListener('click', () => { tag = b.dataset.tag; chips.forEach(x => x.setAttribute('aria-pressed', x === b)); apply(); }));
  q.addEventListener('input', apply);
})();
</script>"""


def card(p, num, href):
    text = html.escape(" ".join([p["title"], p["summary"], p["tag"], re.sub(r"\s+", " ", p["body"])]).lower(), quote=True)
    return f"""<a class="card" href="{href}" data-tag="{html.escape(p['tag'])}" data-text="{text}">
  <div class="art"><span class="num">FILE {num:02d}</span><span aria-hidden="true">{p['icon']}</span></div>
  <div class="body"><h3>{html.escape(p['title'])}</h3><p>{html.escape(p['summary'])}</p>
  <div class="foot"><b>{html.escape(p['tag'])}</b><span>{p['pretty']} · {p['minutes']} min</span></div></div>
</a>"""


def build():
    posts = sorted((parse(f) for f in SRC.glob("*.txt")), key=lambda p: p["date"])
    for i, p in enumerate(posts, 1):
        p["num"] = i
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()

    for i, p in enumerate(posts):
        prev_p = posts[i - 1] if i > 0 else None
        next_p = posts[i + 1] if i + 1 < len(posts) else None
        pager = '<nav class="pager" aria-label="More posts">'
        if prev_p:
            pager += f'<a class="prev" href="{prev_p["slug"]}.html"><small>&lt; PREVIOUS FILE</small>{html.escape(prev_p["title"])}</a>'
        if next_p:
            pager += f'<a class="next" href="{next_p["slug"]}.html"><small>NEXT FILE &gt;</small>{html.escape(next_p["title"])}</a>'
        pager += "</nav>"
        ld = json.dumps({"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
                         "datePublished": p["date"], "description": p["summary"]})
        page = HEAD.format(title=html.escape(p["title"]) + " · Mulder, It's Me", desc=html.escape(p["summary"]), style=STYLE)
        page += f"""<div id="progress"></div>
<header class="masthead"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="kicker" data-decrypt>CASE FILE {p['num']:02d} // {html.escape(p['tag'].upper())}</div>
  <h1>{html.escape(p['title'])}</h1>
  <div class="meta"><span>Filed {p['pretty']}</span><span>{p['minutes']} min read</span><span>By the Basement Desk</span></div>
  <div class="stamp">DECLASSIFIED</div>
</div></header>
<article class="post">
<p class="lede">{html.escape(p['summary'])}</p>
{render_body(p['body'])}
</article>
{pager}
<script type="application/ld+json">{ld}</script>
"""
        page += FOOT.format(stars=STARS, extra=PROGRESS)
        (OUT / f"{p['slug']}.html").write_text(page, encoding="utf-8")

    newest = list(reversed(posts))
    tags = sorted({p["tag"] for p in posts})
    chips = '<button type="button" class="chip" data-tag="all" aria-pressed="true">All files</button>' + "".join(
        f'<button type="button" class="chip" data-tag="{html.escape(t)}" aria-pressed="false">{html.escape(t)}</button>' for t in tags)
    index = HEAD.format(title="Blog · Mulder, It's Me", desc="Essays, guides, and deep dives on The X-Files.", style=STYLE)
    index += f"""<header class="masthead"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="kicker" data-decrypt>THE MULDER, IT'S ME BLOG</div>
  <h1>Field Reports</h1>
  <div class="meta"><span>{len(posts)} declassified files</span><span>Episodes, characters, music, fandom, and paranoia</span></div>
</div></header>
<main class="wrap">
  <div class="tools" role="group" aria-label="Filter posts">{chips}
    <input class="search" id="q" type="search" placeholder="&gt; search the files" aria-label="Search posts"></div>
  <div class="grid">{"".join(card(p, p["num"], p["slug"] + ".html") for p in newest)}</div>
  <p class="empty" id="empty" hidden>NO MATCHING FILES. THE TRUTH IS ELSEWHERE.</p>
</main>
"""
    index += FOOT.format(stars=STARS, extra=INDEX_JS)
    (OUT / "index.html").write_text(index, encoding="utf-8")

    home = HOME.read_text(encoding="utf-8")
    latest = "\n".join(card(p, p["num"], "blog/" + p["slug"] + ".html") for p in newest[:3])
    home = re.sub(r"(<!--BLOG-LATEST-->).*?(<!--/BLOG-LATEST-->)", lambda m: f"{m[1]}\n{latest}\n{m[2]}", home, flags=re.S)
    HOME.write_text(home, encoding="utf-8")
    print(f"built {len(posts)} posts")


if __name__ == "__main__":
    build()
