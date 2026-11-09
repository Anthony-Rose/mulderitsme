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
import subprocess
import urllib.parse

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "posts-src"
OUT = ROOT / "blog"
HOME = ROOT / "index.html"
WPM = 230
SITE_URL = "https://mulderitsme.net"
SITE_NAME = "Mulder, It's Me"
OG_IMAGE = SITE_URL + "/images/og.jpg"
FRAMES = ROOT / "images" / "frames"
LICENSES = {"CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/", "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
            "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/", "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
            "CC BY-SA 3.0 us": "https://creativecommons.org/licenses/by-sa/3.0/us/", "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/"}


def load_credits():
    try:
        return json.loads((FRAMES / "credits.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


CREDITS = load_credits()


def frame_image(slug):
    """Published path of an essay's frame image (images/frames/<slug>.jpg), or None."""
    return f"images/frames/{slug}.jpg" if (FRAMES / f"{slug}.jpg").exists() else None


def credit_html(c):
    lic = c["license"]
    lic_html = f'<a href="{LICENSES[lic]}" rel="noopener">{html.escape(lic)}</a>' if lic in LICENSES else html.escape(lic)
    return (f'<a href="{html.escape(c["source"])}" rel="noopener">{html.escape(c["title"])}</a> by {html.escape(c["author"])}, '
            f'{lic_html}, via Wikimedia Commons')
PUBLISHER = {"@type": "Organization", "@id": SITE_URL + "/#organization", "name": SITE_NAME, "url": SITE_URL + "/",
             "logo": {"@type": "ImageObject", "url": SITE_URL + "/images/logo.png", "width": 512, "height": 512}}
# Byline for the essays: the Basement Desk, a team of AI research and writing
# agents (see about.html). An Organization, never a Person, so it is not
# presented as a human author.
AUTHOR = {"@type": "Organization", "@id": SITE_URL + "/#basement-desk", "name": "The Basement Desk",
          "url": SITE_URL + "/about.html", "description": "A team of AI research and writing agents.",
          "parentOrganization": {"@id": SITE_URL + "/#organization"}}


def crumbs(*trail):
    """BreadcrumbList JSON-LD from (name, path) pairs, starting at the home page."""
    items = [(SITE_NAME, "/")] + list(trail)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": n, "item": SITE_URL + u} for i, (n, u) in enumerate(items, 1)]}


ICONS = ('<link rel="icon" href="/favicon.ico" sizes="32x32">\n<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')


def git_date(*paths):
    """Date (YYYY-MM-DD) of the last commit touching any of paths, or None outside git."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", *map(str, paths)], cwd=ROOT,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def seo(title, desc, path, kind="website", extra_ld=(), image=None):
    """Canonical, Open Graph, Twitter card, icon and JSON-LD tags for one page."""
    url = SITE_URL + path
    t, d = html.escape(title, quote=True), html.escape(desc, quote=True)
    img, iw, ih = (SITE_URL + "/" + image, 1600, 669) if image else (OG_IMAGE, 1200, 630)
    tags = [
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}">',
        f'<meta property="og:type" content="{kind}">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{img}">',
        f'<meta property="og:image:width" content="{iw}"><meta property="og:image:height" content="{ih}"><meta property="og:image:alt" content="{t}">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}"><meta name="twitter:description" content="{d}"><meta name="twitter:image" content="{img}"><meta name="twitter:image:alt" content="{t}">',
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<link rel="alternate" type="application/rss+xml" title="Mulder, It&#x27;s Me journal" href="/feed.xml">',
        ICONS,
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
  .masthead .plate { position:absolute; inset:0; background-size:cover; background-position:center; filter:grayscale(.3) brightness(.5); transform:scale(1.04); animation:drift 30s ease-in-out infinite alternate; }
  .masthead.has-plate canvas { opacity:.35; }
  .masthead.has-plate::before { content:""; position:absolute; inset:0; z-index:0; background:linear-gradient(180deg, rgba(6,9,10,.35), rgba(6,9,10,.55) 55%, var(--bg)); }
  @keyframes drift { from { transform:scale(1.04) translate(0,0); } to { transform:scale(1.1) translate(-1.5%, 1%); } }
  .masthead.has-plate .wrap { padding-top:180px; padding-bottom:90px; }
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
  .sources.imgcredit { border-top:0; padding-top:0; margin-top:-12px; } .sources.imgcredit p { margin:0; }
  .pager { max-width:900px; margin:30px auto 110px; padding:0 16px; display:grid; grid-template-columns:1fr 1fr; gap:24px; }
  .pager a { display:block; text-decoration:none; color:var(--text); padding:22px 0; border-top:1px solid var(--line-2); transition:border-color .2s; }
  .pager a:hover { border-color:var(--green); }
  .pager small { display:block; font:500 11px var(--mono); letter-spacing:.22em; text-transform:uppercase; color:var(--green); margin-bottom:6px; }
  .pager b { font:400 22px/1.25 var(--serif); }
  .pager .next { text-align:right; grid-column:2; }
  .related { padding-top:40px; } .related > h2 { font:500 11px var(--mono); letter-spacing:.24em; text-transform:uppercase; color:var(--soft); margin:0 0 24px; }
  .related .grid { padding-bottom:20px; }

  .tools { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:44px 0 40px; }
  .chip { background:transparent; border:1px solid var(--line-2); color:var(--soft); padding:7px 15px; font:500 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; cursor:pointer; border-radius:999px; transition:.2s; }
  .chip:hover { border-color:var(--green); color:var(--text); }
  .chip[aria-pressed="true"] { background:var(--green); color:#04140a; border-color:var(--green); }
  .search { margin-left:auto; background:transparent; border:0; border-bottom:1px solid var(--line-2); color:var(--text); font:17px var(--read); padding:6px 2px; width:260px; max-width:100%; outline:0; }
  .search:focus { border-color:var(--green); }
  .grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:48px 30px; padding-bottom:120px; }
  .card { position:relative; display:flex; flex-direction:column; color:var(--text); }
  .card :is(h2,h3) a { color:inherit; text-decoration:none; }
  .card :is(h2,h3) a::after { content:""; position:absolute; inset:0; z-index:2; }
  .card :is(h2,h3) a:focus-visible { outline:none; }
  .card:focus-within { outline:2px solid var(--green); outline-offset:6px; }
  .card .frame { position:relative; aspect-ratio:2.39/1; overflow:hidden; border:1px solid var(--line-2); background:#040606; margin-bottom:18px; }
  .card .frame::before { content:""; position:absolute; inset:0; background:radial-gradient(ellipse at var(--fx,50%) 120%, hsla(var(--h,140),80%,60%,.28), transparent 60%), radial-gradient(ellipse at 50% -40%, hsla(var(--h,140),60%,70%,.12), transparent 60%); transition:transform .8s cubic-bezier(.2,.7,.2,1); }
  .card .frame::after { content:""; position:absolute; inset:0; background:repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 1px, transparent 1px 3px); }
  .card:hover .frame::before { transform:scale(1.08); }
  .card .frame .ph { position:absolute; inset:0; background-size:cover; background-position:center; filter:grayscale(.35) contrast(1.05) brightness(.7); transform:scale(1.01); transition:transform 1.2s cubic-bezier(.2,.7,.2,1), filter .6s; }
  .card:hover .frame .ph { transform:scale(1.07); filter:grayscale(0) contrast(1.05) brightness(.85); }
  .card .frame .n { z-index:1; text-shadow:0 4px 30px rgba(0,0,0,.6); position:absolute; left:18px; bottom:6px; font:italic 300 88px/1 var(--serif); color:rgba(243,239,230,.92); letter-spacing:-.03em; transition:transform .6s; }
  .card:hover .frame .n { transform:translateX(6px); }
  .card .frame .tc { z-index:1; position:absolute; right:14px; top:12px; font:500 .75rem var(--mono); letter-spacing:.12em; color:rgba(243,239,230,.55); }
  .card .kick { font:500 .75rem var(--mono); letter-spacing:.12em; text-transform:uppercase; color:var(--green); margin-bottom:8px; }
  .card :is(h2,h3) { font:400 25px/1.15 var(--serif); margin:0 0 10px; color:#f3efe6; transition:color .2s; }
  .card:hover :is(h2,h3) { color:var(--green); }
  .card p { margin:0 0 12px; color:var(--soft); font-size:16px; line-height:1.55; }
  .card .foot { font:12px var(--sans); color:#8f948f; letter-spacing:.04em; margin-top:auto; }
  .card[hidden] { display:none; }
  .empty { color:var(--muted); font:italic 20px var(--read); }
  footer { padding:60px 0 70px; border-top:1px solid var(--line); color:var(--muted); font:13px/1.7 var(--sans); }
  footer .sig { font:italic 300 32px var(--serif); color:var(--text); margin-bottom:10px; }
  footer .site-links { display:flex; flex-wrap:wrap; gap:8px 22px; margin:0 0 20px; font:500 .75rem var(--mono); letter-spacing:.12em; text-transform:uppercase; }
  footer .site-links a { color:var(--soft); text-decoration:none; } footer .site-links a:hover { color:var(--green); }
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

# Site navigation, shared by every page. The nav carries the five main
# destinations; the footer link row adds the section pages and credits.
NAV_PAGES = [("blog/", "Journal"), ("syllabus.html", "Syllabus"), ("filmmakers.html", "Filmmakers"),
             ("reboot.html", "Reboot"), ("glossary.html", "Glossary")]
MORE_PAGES = [("grammar.html", "Visual grammar"), ("lineage.html", "Lineage"), ("about.html", "About"), ("credits.html", "Image credits")]
NAV_LABELS = dict(NAV_PAGES + MORE_PAGES)

# Hand-written section pages at the site root. build() refreshes their head
# tags, nav and footer between marker comments; their bodies are edited by hand.
SECTION_PAGES = {
    "grammar.html": ("Visual Grammar: How the Show Saw",
                     "How The X-Files was lit and heard: six habits, from frames that fall off into true black to a flashlight doing the key light's job, with two palettes."),
    "filmmakers.html": ("Filmmakers: Behind the Camera",
                        "Profiles of the directors, writers, cinematographers and composer who gave The X-Files the feel of a feature film each week, Chris Carter to Mark Snow."),
    "syllabus.html": ("Syllabus: Sixteen Essential Episodes",
                      "Sixteen essential episodes of The X-Files, Pilot to Mulder and Scully Meet the Were-Monster, chosen for what each risked with form, image or sound."),
    "lineage.html": ("Lineage: Influences and Descendants",
                     "A timeline of what The X-Files inherited and what it passed on, from Kolchak and the paranoid thrillers of the 1970s to Fringe, Stranger Things and the Hulu series."),
    "about.html": ("About This Journal",
                   "Who makes Mulder, It's Me, how the X-Files essays are researched and sourced, and what this unofficial film journal is and is not."),
    "reboot.html": ("The Reboot: Coogler's X-Files at Hulu",
                    "Ryan Coogler's X-Files series at Hulu, tracked item by item: what is confirmed, what the trades have reported and what is still only talk."),
}
# Social preview image per section page (1600x669); pages not listed use images/og.jpg.
SECTION_IMAGES = {"grammar.html": "images/frames/home-grammar.jpg"}

LEGAL = ("Mulder, It's Me is an unofficial, non-commercial film journal. It is not affiliated with or endorsed by 20th Century Studios, Fox, "
         "or Ten Thirteen Productions. The X-Files and all related names are trademarks of their respective owners. "
         "Writing and illustrations on this site are original.")

# robots.txt: crawlers that gather text to train AI models are asked to stay out;
# search engines, AI search indexers and on-demand fetchers that answer a reader's
# question stay allowed (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User,
# PerplexityBot, Perplexity-User, meta-externalfetcher, DuckAssistBot, Googlebot,
# Bingbot, Applebot all fall through to the catch-all Allow).
TRAINING_CRAWLERS = ["GPTBot", "ClaudeBot", "anthropic-ai", "Google-Extended", "Applebot-Extended",
                     "CCBot", "Bytespider", "meta-externalagent", "Amazonbot"]
ROBOTS = ("# Training crawlers\n" + "".join(f"User-agent: {b}\n" for b in TRAINING_CRAWLERS) + "Disallow: /\n\n"
          "# Everyone else, including search engines and AI search or user-requested fetchers\n"
          "User-agent: *\nAllow: /\n\n" f"Sitemap: {SITE_URL}/sitemap.xml\n")


def nav_html(prefix, here=None, attrs=""):
    """The site nav. prefix is "" at the root and "../" under blog/; here is the current page's href."""
    links = "".join(f'\n  <a class="link{" here" if h == here else ""}" href="{prefix}{h}"{" aria-current=\"page\"" if h == here else ""}>{t}</a>'
                    for h, t in NAV_PAGES)
    return f'<nav{attrs}><div class="wrap">\n  <a class="brand" href="{prefix or "./"}"><b>Mulder,</b> It\'s Me</a>{links}\n</div></nav>'


def site_links(prefix=""):
    return '<p class="site-links">' + "".join(f'<a href="{prefix}{h}">{t}</a>' for h, t in NAV_PAGES + MORE_PAGES) + "</p>"


def fill(page, marker, content):
    """Replace the text between <!--MARKER--> and <!--/MARKER--> in page."""
    return re.sub(rf"(<!--{marker}-->).*?(<!--/{marker}-->)", lambda m: f"{m[1]}{content}{m[2]}", page, flags=re.S)


def refresh_shell(page, here, solid=True):
    """Nav and footer for a hand-written page at the site root."""
    page = fill(page, "NAV", nav_html("", here, ' id="nav" class="solid"' if solid else ' id="nav"'))
    page = fill(page, "SITE-FOOT", '<div class="sig">The truth is out there.</div>' + site_links())
    return fill(page, "SITE-LEGAL", f'<p>{html.escape(LEGAL, quote=False)} <a href="credits.html">Full image credits</a>.</p>')


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#06090a">
{seo}
{preload}{fonts}
<style>{style}</style>
</head>
<body>
{nav}
"""

FOOT = """<footer><div class="wrap">
  <div class="sig">The truth is out there.</div>
  {links}
  <p>Mulder, It's Me is an unofficial, non-commercial film journal, not affiliated with or endorsed by 20th Century Studios, Fox, or Ten Thirteen Productions.
  The X-Files and all related names are trademarks of their respective owners. <a href="../credits.html" style="color:var(--soft)">Image credits</a>.</p>
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
  const cards = [...document.querySelectorAll('.card')], chips = [...document.querySelectorAll('.chip')], q = document.getElementById('q'), empty = document.getElementById('empty');
  let tag = 'all';
  function apply() { const term = q.value.trim().toLowerCase(); let n = 0;
    cards.forEach(c => { const ok = (tag === 'all' || c.dataset.tag === tag) && (!term || c.dataset.text.includes(term)); c.hidden = !ok; n += ok; });
    empty.hidden = n > 0; }
  function select(t, push) {
    const b = chips.find(x => x.dataset.tag === t) || chips.find(x => x.dataset.tag === 'all');
    tag = b.dataset.tag; chips.forEach(x => x.setAttribute('aria-pressed', x === b)); apply();
    if (push) { const u = new URL(location); tag === 'all' ? u.searchParams.delete('tag') : u.searchParams.set('tag', tag); history.replaceState(null, '', u); }
  }
  chips.forEach(b => b.addEventListener('click', () => select(b.dataset.tag, true)));
  q.addEventListener('input', apply);
  select(new URLSearchParams(location.search).get('tag') || 'all', false);
})();
</script>"""


def card(p, href, prefix="", level=3):
    text = html.escape(" ".join([p["title"], p["summary"], p["tag"], re.sub(r"\s+", " ", p["body"])]).lower(), quote=True)
    tc = f"{p['num']:02d}:{(p['words'] // 60) % 60:02d}:{p['words'] % 60:02d}:{p['num'] * 7 % 24:02d}"
    fx = 20 + (int(p["hue"]) * 7) % 60
    return f"""<article class="card" data-tag="{html.escape(p['tag'])}" data-text="{text}" style="--h:{p['hue']};--fx:{fx}%">
  <div class="frame" aria-hidden="true">{f'<span class="ph" style="background-image:url({prefix}{p["img"]})"></span>' if p.get("img") else ""}<span class="n">{p['num']:02d}</span><span class="tc">{tc}</span></div>
  <div class="kick">{html.escape(p['tag'])}</div>
  <h{level}><a href="{href}">{html.escape(p['title'])}</a></h{level}><p>{html.escape(p['summary'])}</p>
  <div class="foot">{p['pretty']} · {p['minutes']} min read</div>
</article>"""


def build():
    posts = sorted((parse(f) for f in SRC.glob("*.txt")), key=lambda p: (p["date"], p["stem"]))
    for i, p in enumerate(posts, 1):
        p["num"] = i
        p["img"] = frame_image(p["slug"])
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
        near = {q["slug"] for q in (prev_p, next_p) if q} | {p["slug"]}
        related = sorted((q for q in posts if q["slug"] not in near),
                         key=lambda q: (q["tag"] != p["tag"], abs(q["num"] - p["num"])))[:3]
        related_html = (f'<section class="related wrap" aria-labelledby="related-h"><h2 id="related-h">Related essays</h2>'
                        f'<div class="grid">{"".join(card(q, q["slug"] + ".html", "../", 3) for q in related)}</div></section>') if related else ""
        sources = ""
        if p["sources"]:
            items = "".join(f"<li>{inline(l.strip()[2:] if l.strip().startswith('- ') else l.strip())}</li>"
                            for l in p["sources"].splitlines() if l.strip())
            sources = f'<aside class="sources"><h3>Sources and further reading</h3><ul>{items}</ul></aside>'
        if p["img"] and p["slug"] in CREDITS:
            sources += f'<aside class="sources imgcredit"><h3>Header image</h3><p>{credit_html(CREDITS[p["slug"]])}.</p></aside>'
        path = f"/blog/{p['slug']}.html"
        image = ({"@type": "ImageObject", "url": SITE_URL + "/" + p["img"], "width": 1600, "height": 669} if p["img"]
                 else {"@type": "ImageObject", "url": OG_IMAGE, "width": 1200, "height": 630})
        modified = p.get("updated", p["date"])
        article = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"], "description": p["summary"],
                   "datePublished": p["date"], "dateModified": modified, "articleSection": p["tag"],
                   "wordCount": p["words"], "image": image, "inLanguage": "en", "author": AUTHOR, "publisher": PUBLISHER,
                   "mainEntityOfPage": SITE_URL + path, "url": SITE_URL + path,
                   "isPartOf": {"@type": "Blog", "name": SITE_NAME + " journal", "url": SITE_URL + "/blog/"},
                   "about": {"@type": "TVSeries", "name": "The X-Files"}}
        trail = crumbs(("Journal", "/blog/"), (p["title"], path))
        head_tags = seo(p["title"] + " · " + SITE_NAME, p["summary"], path, "article", (article, trail), p["img"])
        head_tags += (f'\n<meta property="article:published_time" content="{p["date"]}"><meta property="article:modified_time" content="{modified}">'
                      f'<meta property="article:section" content="{html.escape(p["tag"], quote=True)}"><meta name="author" content="The Basement Desk">')
        preload = f'<link rel="preload" as="image" href="../{p["img"]}" fetchpriority="high">\n' if p["img"] else ""
        page = HEAD.format(title=html.escape(p["title"]) + " · Mulder, It's Me", desc=html.escape(p["summary"]), seo=head_tags,
                           preload=preload, fonts=FONTS, style=STYLE, nav=nav_html("../"))
        page += f"""<div id="progress"></div>
<header class="masthead{' has-plate' if p['img'] else ''}" style="--h:{p['hue']}">{f'<div class="plate" style="background-image:url(../{p["img"]})"></div>' if p['img'] else ''}<canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="eyebrow">Essay No. {p['num']:02d} · {html.escape(p['tag'])}</div>
  <h1>{inline(p['title'])}</h1>
  <p class="dek">{inline(p['summary'])}</p>
  <div class="meta"><span>{p['pretty']}</span><span>{p['minutes']} min read</span><span>{p['words']:,} words</span></div>
</div></header>
<article class="post">
{render_body(p['body'])}
</article>
{sources}
{related_html}
{pager}
"""
        page += FOOT.format(links=site_links("../"), stars=STARS, extra=PROGRESS)
        (OUT / f"{p['slug']}.html").write_text(page, encoding="utf-8")

    newest = list(reversed(posts))
    tags = sorted({p["tag"] for p in posts})
    chips = '<button type="button" class="chip" data-tag="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="chip" data-tag="{html.escape(t)}" aria-pressed="false">{html.escape(t)}</button>' for t in tags)
    jdesc = "Long-form essays on The X-Files as film and television craft: direction, cinematography, form, music, influence and legacy."
    blog_ld = {"@context": "https://schema.org", "@type": "Blog", "name": SITE_NAME + " journal", "url": SITE_URL + "/blog/", "publisher": PUBLISHER,
               "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": f"{SITE_URL}/blog/{p['slug']}.html", "datePublished": p["date"]} for p in newest]}
    index = HEAD.format(title="Journal: Essays on The X-Files · Mulder, It's Me", desc=html.escape(jdesc),
                        seo=seo("Journal: Essays on The X-Files", jdesc, "/blog/", "website", (blog_ld, crumbs(("Journal", "/blog/")))), preload="", fonts=FONTS, style=STYLE, nav=nav_html("../", "blog/"))
    index += f"""<header class="masthead"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="eyebrow">The Journal</div>
  <h1>Essays on The X-Files</h1>
  <p class="dek">Direction, cinematography, form, music, influence and legacy. {len(posts)} essays and counting.</p>
</div></header>
<main class="wrap">
  <div class="tools" role="group" aria-label="Filter essays">{chips}
    <input class="search" id="q" type="search" placeholder="Search the essays" aria-label="Search essays"></div>
  <div class="grid">{"".join(card(p, p["slug"] + ".html", "../", 2) for p in newest)}</div>
  <p class="empty" id="empty" hidden>Nothing matches. The truth is elsewhere.</p>
</main>
"""
    index += FOOT.format(links=site_links("../"), stars=STARS, extra=INDEX_JS)
    (OUT / "index.html").write_text(index, encoding="utf-8")

    home = HOME.read_text(encoding="utf-8")
    latest = "\n".join(card(p, "blog/" + p["slug"] + ".html") for p in newest[:3])
    home = re.sub(r"(<!--BLOG-LATEST-->).*?(<!--/BLOG-LATEST-->)", lambda m: f"{m[1]}\n{latest}\n{m[2]}", home, flags=re.S)
    browse = "".join(f'<a class="tagpill" href="blog/?tag={urllib.parse.quote(t)}">{html.escape(t)}</a>' for t in tags)
    home = re.sub(r"(<!--BROWSE-TAGS-->).*?(<!--/BROWSE-TAGS-->)", lambda m: f"{m[1]}{browse}{m[2]}", home, flags=re.S)
    home = refresh_shell(render_reboot(home), None, solid=False)
    try:
        qdata = json.loads((ROOT / "data_quotes.json").read_text(encoding="utf-8"))
        qarr = [{"q": it["quote"], "a": (f'{it["speaker"]} · {it["source"].split(",")[0]}' if it["speaker"] else it["source"])} for it in qdata]
        qjson = json.dumps(qarr, ensure_ascii=False)
        home = re.sub(r"(<!--QUOTES-->).*?(<!--/QUOTES-->)", lambda m: f"{m[1]}{qjson}{m[2]}", home, flags=re.S)
    except FileNotFoundError:
        pass
    hdesc = ("A film journal on The X-Files: long-form essays on its direction, cinematography, form, music and legacy, "
             "with a viewing syllabus and filmmaker profiles.")
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "@id": SITE_URL + "/#website", "name": SITE_NAME, "url": SITE_URL + "/", "description": hdesc,
               "inLanguage": "en", "publisher": PUBLISHER}
    home_tags = seo(SITE_NAME + ": A Film Journal on The X-Files", hdesc, "/", "website", (site_ld,))
    home = re.sub(r"(<!--SEO-->).*?(<!--/SEO-->)", lambda m: f"{m[1]}\n{home_tags}\n{m[2]}", home, flags=re.S)
    home = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{html.escape(hdesc, quote=True)}">', home, count=1)
    HOME.write_text(home, encoding="utf-8")
    for name, (title, desc) in SECTION_PAGES.items():
        f = ROOT / name
        page = f.read_text(encoding="utf-8")
        short = NAV_LABELS.get(name, title.split(":")[0])
        page_ld = {"@context": "https://schema.org", "@type": "AboutPage" if name == "about.html" else "WebPage", "name": title, "description": desc, "url": f"{SITE_URL}/{name}",
                   "inLanguage": "en", "isPartOf": {"@type": "WebSite", "@id": SITE_URL + "/#website", "name": SITE_NAME, "url": SITE_URL + "/"},
                   "publisher": PUBLISHER, "about": {"@type": "TVSeries", "name": "The X-Files"}}
        if name == "about.html":
            page_ld["mainEntity"] = [{"@id": PUBLISHER["@id"]}, AUTHOR]
        head = (f"<title>{html.escape(title)} · {html.escape(SITE_NAME)}</title>\n"
                f'<meta name="description" content="{html.escape(desc, quote=True)}">\n'
                + seo(title, desc, "/" + name, "website", (page_ld, crumbs((short, "/" + name))), SECTION_IMAGES.get(name)))
        page = refresh_shell(fill(page, "SEO", "\n" + head + "\n"), name)
        if name == "reboot.html":
            page = render_reboot(page)
        f.write_text(page, encoding="utf-8")
    write_feeds(newest)
    write_credits()
    write_glossary()
    print(f"built {len(posts)} posts, plus sitemap.xml, feed.xml and robots.txt")


def render_reboot(home):
    try:
        data = json.loads((ROOT / "data_reboot.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return home
    glyph = {"confirmed": "▲", "reported": "◆", "rumored": "▽"}

    def tk(it):
        # The ticker is a visual extra for pointer users; the ledger below it
        # carries the same items for keyboard and screen reader users.
        g = glyph.get(it["status"], "●")
        extra = ' tabindex="-1"'
        return (f'<button type="button" class="tk"{extra} aria-expanded="false" data-status="{html.escape(it["status"])}"'
                f' data-label="{html.escape(it["label"], quote=True)}" data-text="{html.escape(it["text"], quote=True)}">'
                f'<span class="tkg" aria-hidden="true">{g}</span>'
                f'<span class="tkl">{html.escape(it["label"])}</span>'
                f'<span class="tks">{html.escape(it["status"].capitalize())}</span></button>')
    its = data.get("items", [])
    track = "".join(tk(it) for it in its) * 2
    order = {"confirmed": 0, "reported": 1, "rumored": 2}
    li = "".join(f'<li data-status="{html.escape(it["status"])}"><b>{html.escape(it["label"])}</b>'
                 f'<span class="st">{html.escape(it["status"].capitalize())}</span><p>{html.escape(it["text"])}</p></li>'
                 for it in sorted(its, key=lambda it: order.get(it["status"], 3)))
    updated = f'<span class="updated">Updated {html.escape(data.get("updated", ""))}</span>'
    counts = {s: sum(it["status"] == s for it in its) for s in ("confirmed", "reported", "rumored")}
    line = ('<span class="rl-lead">The reboot ledger:</span> '
            + ", ".join(f'<span class="rl-{s[:4]}">{n} {s}</span>' for s, n in counts.items() if n)
            + f' <span class="rl-sep" aria-hidden="true">·</span> {updated} <span class="rl-sep" aria-hidden="true">·</span> '
            '<a href="reboot.html">See every item</a>')
    home = re.sub(r"(<!--REBOOT-LINE-->).*?(<!--/REBOOT-LINE-->)", lambda m: f"{m[1]}{line}{m[2]}", home, flags=re.S)
    home = re.sub(r"(<!--REBOOT-DEK-->).*?(<!--/REBOOT-DEK-->)", lambda m: f"{m[1]}{html.escape(data.get('dek', ''))}{m[2]}", home, flags=re.S)
    home = re.sub(r"(<!--REBOOT-TICK-->).*?(<!--/REBOOT-TICK-->)", lambda m: f"{m[1]}{track}{m[2]}", home, flags=re.S)
    home = re.sub(r"(<!--REBOOT-LIST-->).*?(<!--/REBOOT-LIST-->)", lambda m: f"{m[1]}{li}{m[2]}", home, flags=re.S)
    home = re.sub(r"(<!--REBOOT-UPDATED-->).*?(<!--/REBOOT-UPDATED-->)", lambda m: f"{m[1]}{updated}{m[2]}", home, flags=re.S)
    return home


def write_glossary():
    try:
        data = json.loads((ROOT / "data_glossary.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    gdesc = ("A field guide to the mythology of The X-Files: the Syndicate, the colonists, the black oil, "
             "the informants and the people of the basement office.")
    rows = "".join(f'<div class="gterm"><dt>{html.escape(e["term"])}</dt><dd>{html.escape(e["def"])}</dd></div>' for e in data)
    gstyle = (
        "  .glossary { max-width: 820px; margin: 0 auto; padding: 0 16px 120px; }\n"
        "  .glossary dl { margin: 0; }\n"
        "  .gterm { padding: 24px 0; border-top: 1px solid var(--line); display: grid; grid-template-columns: 240px 1fr; gap: 28px; align-items: start; }\n"
        "  .gterm dt { font: 400 22px/1.25 var(--serif); color: #f3efe6; }\n"
        "  .gterm dd { margin: 0; color: var(--soft); font: 16px/1.65 var(--read); }\n"
        "  @media (max-width: 680px) { .gterm { grid-template-columns: 1fr; gap: 6px; } }\n")
    gtitle = "Glossary: The Mythology of The X-Files"
    terms = {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": gtitle, "description": gdesc, "url": SITE_URL + "/glossary.html",
             "hasDefinedTerm": [{"@type": "DefinedTerm", "name": e["term"], "description": e["def"]} for e in data]}
    seo_tags = seo(gtitle, gdesc, "/glossary.html", "website", (terms, crumbs(("Glossary", "/glossary.html"))))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(gtitle)} · {html.escape(SITE_NAME)}</title>
<meta name="description" content="{html.escape(gdesc, quote=True)}">
<meta name="theme-color" content="#06090a">
{seo_tags}
{FONTS}
<style>{STYLE}{gstyle}</style>
</head>
<body>
{nav_html("", "glossary.html")}
<header class="masthead"><canvas id="stars" aria-hidden="true"></canvas><div class="wrap">
  <div class="eyebrow">Field guide</div>
  <h1>A glossary of the mythology</h1>
  <p class="dek">{html.escape(gdesc)}</p>
</div></header>
<main class="glossary"><dl>{rows}</dl></main>
<footer><div class="wrap">
  <div class="sig">The truth is out there.</div>
  {site_links()}
  <p>Mulder, It's Me is an unofficial, non-commercial film journal, not affiliated with or endorsed by 20th Century Studios, Fox, or Ten Thirteen Productions.
  The X-Files and all related names are trademarks of their respective owners. <a href="credits.html" style="color:var(--soft)">Image credits</a>.</p>
</div></footer>
<script>{STARS}</script>
</body>
</html>
"""
    (ROOT / "glossary.html").write_text(page, encoding="utf-8")


def write_credits():
    rows = "".join(f'<li><img src="{html.escape(c["file"])}" alt="" width="120" height="68" loading="lazy" decoding="async"><div><b>{html.escape(k.replace("cast-", "").replace("p-", "").replace("-", " ").title())}</b>{credit_html(c)}</div></li>'
                   for k, c in sorted(CREDITS.items()))
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Image credits · {html.escape(SITE_NAME)}</title><meta name="robots" content="noindex, follow"><link rel="canonical" href="{SITE_URL}/credits.html">
{ICONS}
{FONTS}
<style>body{{margin:0;background:#06090a;color:#e6e2d8;font:16px/1.6 "IBM Plex Sans",system-ui,sans-serif}} .w{{max-width:900px;margin:0 auto;padding:60px 16px 90px}}
h1{{font:300 48px/1.1 "Fraunces",Georgia,serif;margin:0 0 10px}} p.l{{color:#b9b5aa;margin:0 0 36px}} a{{color:#b9b5aa}} ul{{list-style:none;padding:0;margin:0;display:grid;gap:14px}}
li{{display:flex;gap:16px;align-items:center;border-top:1px solid #1c2528;padding-top:14px}} li img{{width:120px;height:68px;object-fit:cover;flex:none;filter:grayscale(.3)}}
li b{{display:block;font:500 12px "IBM Plex Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:#6dff8a}} .back{{display:inline-block;margin-bottom:30px;color:#6dff8a;text-decoration:none;font:500 12px "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase}}</style>
</head><body><div class="w"><a class="back" href="./">&larr; Mulder, It's Me</a><h1>Image credits</h1>
<p class="l">Every photograph on this site is freely licensed or in the public domain, from Wikimedia Commons. Images were cropped, resized and toned for the layout; adapted copies are shared under the same licenses. No stills from The X-Files are used.</p>
<ul>{rows}</ul></div></body></html>
"""
    (ROOT / "credits.html").write_text(page, encoding="utf-8")


def write_feeds(newest):
    today = datetime.date.today().isoformat()
    latest = max((p.get("updated", p["date"]) for p in newest), default=today)
    # lastmod comes from the last commit that touched each page's source, so a rebuild alone does not
    # make every page look freshly changed.
    urls = [("/", max(latest, git_date("index.html", "data_reboot.json") or latest), "weekly", "1.0"),
            ("/blog/", latest, "weekly", "0.9")]
    urls += [("/" + name, git_date(name, *(["data_reboot.json"] if name == "reboot.html" else [])) or today, "monthly", "0.7")
             for name in SECTION_PAGES]
    urls += [("/glossary.html", git_date("data_glossary.json") or today, "monthly", "0.6")]
    urls += [(f"/blog/{p['slug']}.html", p.get("updated", p["date"]), "monthly", "0.8") for p in newest]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{m}</lastmod></url>\n" for u, m, *_ in urls)
        + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(ROBOTS, encoding="utf-8")

    def rfc822(d):
        return datetime.datetime.combine(datetime.date.fromisoformat(d), datetime.time(12)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "".join(
        f"  <item><title>{html.escape(p['title'])}</title><link>{SITE_URL}/blog/{p['slug']}.html</link>"
        f"<guid>{SITE_URL}/blog/{p['slug']}.html</guid><pubDate>{rfc822(p['date'])}</pubDate>"
        f"<category>{html.escape(p['tag'])}</category><description>{html.escape(p['summary'])}</description></item>\n"
        for p in newest[:30])
    (ROOT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>\n'
        f"  <title>{html.escape(SITE_NAME)}</title><link>{SITE_URL}/</link>"
        f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
        "<description>Essays on The X-Files as film and television craft.</description><language>en</language>"
        f"<lastBuildDate>{rfc822(newest[0]['date']) if newest else ''}</lastBuildDate>\n"
        + items + "</channel></rss>\n", encoding="utf-8")


if __name__ == "__main__":
    build()
