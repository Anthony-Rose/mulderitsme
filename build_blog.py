"""Build the journal from posts-src/*.txt.

Each post file is a few `key: value` header lines, a `---` line, then the body.

Header keys: title, date (YYYY-MM-DD), tag, summary, and optionally hue
(0-360, tints the card art).

Body syntax: blank-line separated paragraphs, `## ` headings, `- ` bullet
lists, `> ` pull quotes, *italics* for titles, and [links](https://...).
A final block that starts with a `Sources:` line becomes the sources list,
one `- [label](url)` per line under it.

Run `python build_blog.py` after adding or editing a post. It rewrites blog/
and the journal strip on the homepage (between the BLOG-LATEST markers).
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
WPM = 230
SITE_URL = "https://mulderitsme.net"
SITE_NAME = "Mulder, It's Me"
OG_IMAGE = SITE_URL + "/images/og.jpg"
PUBLISHER = {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL + "/",
             "logo": {"@type": "ImageObject", "url": OG_IMAGE}}


def seo(title, desc, path, kind="website", extra_ld=()):
    """Canonical, Open Graph, Twitter card and JSON-LD tags for one page."""
    url = SITE_URL + path
    t, d = html.escape(title, quote=True), html.escape(desc, quote=True)
    tags = [
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}">',
        f'<meta property="og:type" content="{kind}">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}"><meta name="twitter:description" content="{d}"><meta name="twitter:image" content="{OG_IMAGE}">',
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<link rel="alternate" type="application/rss+xml" title="Mulder, It&#x27;s Me journal" href="/feed.xml">',
    ]
    for ld in extra_ld:
        tags.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>')
    return "\n".join(tags)


def parse(path):
    head, body = path.read_text(encoding="utf-8").split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    meta["stem"] = path.stem
    meta["slug"] = re.sub(r"^\d+-", "", path.stem)
    body = body.strip()
    sources = ""
    m = re.search(r"(?:^|\n\s*\n)Sources:\s*\n(.+)$", body, flags=re.S)
    if m:
        sources, body = m[1].strip(), body[: m.start()].strip()
    meta["body"], meta["sources"] = body, sources
    meta["words"] = len(body.split())
    meta["minutes"] = max(1, round(meta["words"] / WPM))
    d = datetime.date.fromisoformat(meta["date"])
    meta["pretty"] = d.strftime("%B %d, %Y").replace(" 0", " ")
    meta.setdefault("hue", str(sum(map(ord, meta["slug"])) * 37 % 360))
    return meta


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m[2])}" rel="noopener">{m[1]}</a>', text)
    return re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)


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
        elif all(l.startswith("> ") for l in lines):
            out.append(f"<blockquote>{inline(' '.join(l[2:] for l in lines))}</blockquote>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;1,9..144,300;1,9..144,400'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500'
         '&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">')

STYLE = """
  :root { --bg:#06090a; --line:#1c2528; --line-2:#2a3539; --text:#e6e2d8; --soft:#b9b5aa; --muted:#858a84; --green:#6dff8a; --green-dim:#3d8f52; --amber:#d9b56a;
    --serif:"Fraunces", Georgia, serif; --read:"Source Serif 4", Georgia, serif; --sans:"IBM Plex Sans", system-ui, sans-serif; --mono:"IBM Plex Mono", ui-monospace, monospace; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:19px/1.75 var(--read); overflow-x:hidden; }
  body::before { content:""; position:fixed; inset:-50%; pointer-events:none; z-index:70; opacity:.05;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    animation:grain 1.2s steps(6) infinite; }
  @keyframes grain { 0%{transform:translate(0,0)} 25%{transform:translate(-3%,2%)} 50%{transform:translate(2%,-3%)} 75%{transform:translate(3%,3%)} 100%{transform:translate(0,0)} }
  ::selection { background:var(--green); color:#000; }
  a { color:inherit; }
  .wrap { max-width:1180px; margin:0 auto; padding:0 16px; }
  nav { position:sticky; top:0; z-index:40; background:rgba(6,9,10,.9); backdrop-filter:blur(10px); border-bottom:1px solid var(--line); }
  nav .wrap { display:flex; gap:26px; align-items:center; height:60px; overflow-x:auto; scrollbar-width:none; }
  nav .brand { font:italic 400 22px var(--serif); color:var(--text); text-decoration:none; white-space:nowrap; margin-right:auto; }
  nav .brand b { font-style:normal; font-weight:500; color:var(--green); }
  nav a.link { font:500 12px var(--sans); letter-spacing:.14em; text-transform:uppercase; color:var(--soft); text-decoration:none; white-space:nowrap; }
  nav a.link:hover, nav a.link.here { color:var(--green); }
  #progress { position:fixed; top:0; left:0; height:2px; width:0; background:var(--green); box-shadow:0 0 10px var(--green); z-index:60; }

  .masthead { position:relative; overflow:hidden; border-bottom:1px solid var(--line); }
  .masthead canvas { position:absolute; inset:0; width:100%; height:100%; opacity:.8; }
  .masthead::after { content:""; position:absolute; inset:0; background:radial-gradient(ellipse at 50% 140%, hsla(var(--h,140),70%,45%,.28), transparent 65%); pointer-events:none; }
  .masthead .wrap { position:relative; z-index:1; padding-top:110px; padding-bottom:80px; max-width:920px; }
  .eyebrow { font:500 12px var(--mono); letter-spacing:.28em; text-transform:uppercase; color:var(--green); }
  h1 { font:300 clamp(40px, 6.8vw, 82px)/1.02 var(--serif); letter-spacing:-.02em; margin:.25em 0 .3em; color:#f3efe6; }
  .dek { font:italic 400 clamp(19px, 2.3vw, 24px)/1.5 var(--read); color:var(--soft); margin:0 0 28px; max-width:760px; }
  .meta { font:13px var(--sans); color:var(--muted); display:flex; flex-wrap:wrap; gap:6px 22px; letter-spacing:.03em; }

  article.post { max-width:700px; margin:0 auto; padding:72px 16px 30px; }
  article.post > p:first-of-type::first-letter { float:left; font:400 86px/.82 var(--serif); padding:8px 12px 0 0; color:var(--green); }
  article.post p { margin:0 0 1.25em; }
  article.post a { color:var(--green); text-decoration-thickness:1px; text-underline-offset:3px; }
  article.post h2 { font:400 30px/1.2 var(--serif); color:#f3efe6; margin:2.2em 0 .6em; letter-spacing:-.01em; }
  article.post ul { padding-left:22px; margin:0 0 1.3em; } article.post li { margin:6px 0; } article.post li::marker { color:var(--green); }
  article.post blockquote { margin:1.8em -40px; padding:6px 0 6px 34px; border-left:2px solid var(--green); font:italic 300 clamp(24px, 3vw, 32px)/1.35 var(--serif); color:#f3efe6; }
  .sources { max-width:700px; margin:0 auto 40px; padding:28px 16px 0; border-top:1px solid var(--line); font:14px/1.6 var(--sans); color:var(--muted); }
  .sources h3 { font:500 11px var(--mono); letter-spacing:.24em; text-transform:uppercase; color:var(--soft); margin:0 0 10px; }
  .sources ul { margin:0; padding-left:18px; } .sources a { color:var(--soft); }
  .pager { max-width:900px; margin:30px auto 110px; padding:0 16px; display:grid; grid-template-columns:1fr 1fr; gap:24px; }
  .pager a { display:block; text-decoration:none; color:var(--text); padding:22px 0; border-top:1px solid var(--line-2); transition:border-color .2s; }
  .pager a:hover { border-color:var(--green); }
  .pager small { display:block; font:500 11px var(--mono); letter-spacing:.22em; text-transform:uppercase; color:var(--green); margin-bottom:6px; }
  .pager b { font:400 22px/1.25 var(--serif); }
  .pager .next { text-align:right; grid-column:2; }

  .tools { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:44px 0 40px; }
  .chip { background:transparent; border:1px solid var(--line-2); color:var(--soft); padding:7px 15px; font:500 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; cursor:pointer; border-radius:999px; transition:.2s; }
  .chip:hover { border-color:var(--green); color:var(--text); }
  .chip[aria-pressed="true"] { background:var(--green); color:#04140a; border-color:var(--green); }
  .search { margin-left:auto; background:transparent; border:0; border-bottom:1px solid var(--line-2); color:var(--text); font:17px var(--read); padding:6px 2px; width:260px; max-width:100%; outline:0; }
  .search:focus { border-color:var(--green); }
  .grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:48px 30px; padding-bottom:120px; }
  .card { display:flex; flex-direction:column; text-decoration:none; color:var(--text); }
  .card .frame { position:relative; aspect-ratio:2.39/1; overflow:hidden; border:1px solid var(--line-2); background:#040606; margin-bottom:18px; }
  .card .frame::before { content:""; position:absolute; inset:0; background:radial-gradient(ellipse at var(--fx,50%) 120%, hsla(var(--h,140),80%,60%,.28), transparent 60%), radial-gradient(ellipse at 50% -40%, hsla(var(--h,140),60%,70%,.12), transparent 60%); transition:transform .8s cubic-bezier(.2,.7,.2,1); }
  .card .frame::after { content:""; position:absolute; inset:0; background:repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 1px, transparent 1px 3px); }
  .card:hover .frame::before { transform:scale(1.08); }
  .card .frame .n { position:absolute; left:18px; bottom:6px; font:italic 300 88px/1 var(--serif); color:rgba(243,239,230,.92); letter-spacing:-.03em; transition:transform .6s; }
  .card:hover .frame .n { transform:translateX(6px); }
  .card .frame .tc { position:absolute; right:14px; top:12px; font:500 11px var(--mono); letter-spacing:.14em; color:rgba(243,239,230,.55); }
  .card .kick { font:500 11px var(--mono); letter-spacing:.2em; text-transform:uppercase; color:var(--green); margin-bottom:8px; }
  .card h3 { font:400 25px/1.15 var(--serif); margin:0 0 10px; color:#f3efe6; transition:color .2s; }
  .card:hover h3 { color:var(--green); }
  .card p { margin:0 0 12px; color:var(--soft); font-size:16px; line-height:1.55; }
  .card .foot { font:12px var(--sans); color:var(--muted); letter-spacing:.04em; margin-top:auto; }
  .card[hidden] { display:none; }
  .empty { color:var(--muted); font:italic 20px var(--read); }
  footer { padding:60px 0 70px; border-top:1px solid var(--line); color:var(--muted); font:13px/1.7 var(--sans); }
  footer .sig { font:italic 300 32px var(--serif); color:var(--text); margin-bottom:10px; }
  @media (max-width:980px) { .grid { grid-template-columns:1fr 1fr; } article.post blockquote { margin:1.6em 0; } }
  @media (max-width:640px) { body { font-size:17.5px; } .grid { grid-template-columns:1fr; } .search { margin-left:0; width:100%; } .pager { grid-template-columns:1fr; } .pager .next { grid-column:1; text-align:left; } }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
"""

STARS = """
(() => {
  const c = document.getElementById('stars'); if (!c) return;
  const x = c.getContext('2d'), still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let w, h, s = [];
  function size() { const r = devicePixelRatio || 1; w = c.clientWidth; h = c.clientHeight; c.width = w * r; c.height = h * r; x.setTransform(r, 0, 0, r, 0, 0);
    s = Array.from({ length: Math.round(w * h / 2200) }, () => ({ x: Math.random() * w, y: Math.random() * h, r: Math.random() ** 3 * 1.5 + .3, p: Math.random() * 6, v: Math.random() * .06 + .015 })); }
  function draw(t) { x.clearRect(0, 0, w, h);
    for (const a of s) { a.x -= a.v; if (a.x < 0) a.x = w; x.globalAlpha = .3 + .6 * Math.abs(Math.sin(t / 1500 + a.p)); x.fillStyle = '#e8f0e6'; x.beginPath(); x.arc(a.x, a.y, a.r, 0, 7); x.fill(); }
    if (!still) requestAnimationFrame(draw); }
  addEventListener('resize', size); size(); requestAnimationFrame(draw);
})();
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#06090a">
{seo}
{fonts}
<style>{style}</style>
</head>
<body>
<nav><div class="wrap">
  <a class="brand" href="../"><b>Mulder,</b> It's Me</a>
  <a class="link" href="../#grammar">Visual grammar</a>
  <a class="link" href="../#people">Filmmakers</a>
  <a class="link" href="../#syllabus">Syllabus</a>
  <a class="link here" href="./">Journal</a>
</div></nav>
"""

FOOT = """<footer><div class="wrap">
  <div class="sig">The truth is out there.</div>
  <p>Mulder, It's Me is an unofficial, non-commercial film journal, not affiliated with or endorsed by 20th Century Studios, Fox, or Ten Thirteen Productions.
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


def card(p, href):
    text = html.escape(" ".join([p["title"], p["summary"], p["tag"], re.sub(r"\s+", " ", p["body"])]).lower(), quote=True)
    tc = f"{p['num']:02d}:{(p['words'] // 60) % 60:02d}:{p['words'] % 60:02d}:{p['num'] * 7 % 24:02d}"
    fx = 20 + (int(p["hue"]) * 7) % 60
    return f"""<a class="card" href="{href}" data-tag="{html.escape(p['tag'])}" data-text="{text}" style="--h:{p['hue']};--fx:{fx}%">
  <div class="frame" aria-hidden="true"><span class="n">{p['num']:02d}</span><span class="tc">{tc}</span></div>
  <div class="kick">{html.escape(p['tag'])}</div>
  <h3>{html.escape(p['title'])}</h3><p>{html.escape(p['summary'])}</p>
  <div class="foot">{p['pretty']} · {p['minutes']} min read</div>
</a>"""


def build():
    posts = sorted((parse(f) for f in SRC.glob("*.txt")), key=lambda p: (p["date"], p["stem"]))
    for i, p in enumerate(posts, 1):
        p["num"] = i
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()

    for i, p in enumerate(posts):
        prev_p = posts[i - 1] if i > 0 else None
        next_p = posts[i + 1] if i + 1 < len(posts) else None
        pager = '<nav class="pager" aria-label="More essays">'
        if prev_p:
            pager += f'<a class="prev" href="{prev_p["slug"]}.html"><small>Previous essay</small><b>{html.escape(prev_p["title"])}</b></a>'
        if next_p:
            pager += f'<a class="next" href="{next_p["slug"]}.html"><small>Next essay</small><b>{html.escape(next_p["title"])}</b></a>'
        pager += "</nav>"
        sources = ""
        if p["sources"]:
            items = "".join(f"<li>{inline(l.strip()[2:] if l.strip().startswith('- ') else l.strip())}</li>"
                            for l in p["sources"].splitlines() if l.strip())
            sources = f'<aside class="sources"><h3>Sources and further reading</h3><ul>{items}</ul></aside>'
        path = f"/blog/{p['slug']}.html"
        article = {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["summary"],
                   "datePublished": p["date"], "dateModified": p.get("updated", p["date"]), "articleSection": p["tag"],
                   "wordCount": p["words"], "image": OG_IMAGE, "inLanguage": "en", "author": PUBLISHER, "publisher": PUBLISHER,
                   "mainEntityOfPage": SITE_URL + path, "about": {"@type": "TVSeries", "name": "The X-Files"}}
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Journal", "item": SITE_URL + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": SITE_URL + path}]}
        head_tags = seo(p["title"] + " · " + SITE_NAME, p["summary"], path, "article", (article, crumbs))
        head_tags += f'\n<meta property="article:published_time" content="{p["date"]}"><meta property="article:section" content="{html.escape(p["tag"], quote=True)}">'
        page = HEAD.format(title=html.escape(p["title"]) + " · Mulder, It's Me", desc=html.escape(p["summary"]), seo=head_tags, fonts=FONTS, style=STYLE)
        page += f"""<div id="progress"></div>
<header class="masthead" style="--h:{p['hue']}"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="eyebrow">Essay No. {p['num']:02d} · {html.escape(p['tag'])}</div>
  <h1>{inline(p['title'])}</h1>
  <p class="dek">{inline(p['summary'])}</p>
  <div class="meta"><span>{p['pretty']}</span><span>{p['minutes']} min read</span><span>{p['words']:,} words</span></div>
</div></header>
<article class="post">
{render_body(p['body'])}
</article>
{sources}
{pager}
"""
        page += FOOT.format(stars=STARS, extra=PROGRESS)
        (OUT / f"{p['slug']}.html").write_text(page, encoding="utf-8")

    newest = list(reversed(posts))
    tags = sorted({p["tag"] for p in posts})
    chips = '<button type="button" class="chip" data-tag="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="chip" data-tag="{html.escape(t)}" aria-pressed="false">{html.escape(t)}</button>' for t in tags)
    jdesc = "Long-form essays on The X-Files as film and television craft: direction, cinematography, form, music, influence and legacy."
    blog_ld = {"@context": "https://schema.org", "@type": "Blog", "name": SITE_NAME + " journal", "url": SITE_URL + "/blog/", "publisher": PUBLISHER,
               "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": f"{SITE_URL}/blog/{p['slug']}.html", "datePublished": p["date"]} for p in newest]}
    index = HEAD.format(title="Journal: Essays on The X-Files · Mulder, It's Me", desc=html.escape(jdesc),
                        seo=seo("Journal: Essays on The X-Files", jdesc, "/blog/", "website", (blog_ld,)), fonts=FONTS, style=STYLE)
    index += f"""<header class="masthead"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="eyebrow">The Journal</div>
  <h1>Essays on The X-Files</h1>
  <p class="dek">Direction, cinematography, form, music, influence and legacy. {len(posts)} essays and counting.</p>
</div></header>
<main class="wrap">
  <div class="tools" role="group" aria-label="Filter essays">{chips}
    <input class="search" id="q" type="search" placeholder="Search the essays" aria-label="Search essays"></div>
  <div class="grid">{"".join(card(p, p["slug"] + ".html") for p in newest)}</div>
  <p class="empty" id="empty" hidden>Nothing matches. The truth is elsewhere.</p>
</main>
"""
    index += FOOT.format(stars=STARS, extra=INDEX_JS)
    (OUT / "index.html").write_text(index, encoding="utf-8")

    home = HOME.read_text(encoding="utf-8")
    latest = "\n".join(card(p, "blog/" + p["slug"] + ".html") for p in newest[:4])
    home = re.sub(r"(<!--BLOG-LATEST-->).*?(<!--/BLOG-LATEST-->)", lambda m: f"{m[1]}\n{latest}\n{m[2]}", home, flags=re.S)
    hdesc = ("A film journal on The X-Files: long-form essays on its direction, cinematography, form, music and legacy, "
             "with a viewing syllabus and filmmaker profiles.")
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/", "description": hdesc,
               "inLanguage": "en", "publisher": PUBLISHER}
    home_tags = seo(SITE_NAME + ": A Film Journal on The X-Files", hdesc, "/", "website", (site_ld,))
    home = re.sub(r"(<!--SEO-->).*?(<!--/SEO-->)", lambda m: f"{m[1]}\n{home_tags}\n{m[2]}", home, flags=re.S)
    HOME.write_text(home, encoding="utf-8")
    write_feeds(newest)
    print(f"built {len(posts)} posts, plus sitemap.xml, feed.xml and robots.txt")


def write_feeds(newest):
    today = datetime.date.today().isoformat()
    urls = [("/", today, "weekly", "1.0"), ("/blog/", newest[0]["date"] if newest else today, "weekly", "0.9")]
    urls += [(f"/blog/{p['slug']}.html", p.get("updated", p["date"]), "monthly", "0.8") for p in newest]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{m}</lastmod><changefreq>{c}</changefreq><priority>{pr}</priority></url>\n"
                  for u, m, c, pr in urls)
        + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")

    def rfc822(d):
        return datetime.datetime.combine(datetime.date.fromisoformat(d), datetime.time(12)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "".join(
        f"  <item><title>{html.escape(p['title'])}</title><link>{SITE_URL}/blog/{p['slug']}.html</link>"
        f"<guid>{SITE_URL}/blog/{p['slug']}.html</guid><pubDate>{rfc822(p['date'])}</pubDate>"
        f"<category>{html.escape(p['tag'])}</category><description>{html.escape(p['summary'])}</description></item>\n"
        for p in newest[:30])
    (ROOT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
        f"  <title>{html.escape(SITE_NAME)}</title><link>{SITE_URL}/</link>"
        "<description>Essays on The X-Files as film and television craft.</description><language>en</language>\n"
        + items + "</channel></rss>\n", encoding="utf-8")


if __name__ == "__main__":
    build()
