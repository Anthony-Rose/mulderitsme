# Mulder, It's Me

An unofficial film journal on The X-Files, served at https://mulderitsme.net from GitHub Pages. DNS is at Cloudflare, with records set to "DNS only".

## Layout

- `index.html` is the front page: the WebGL UFO hero (three.js from jsDelivr), a one-line reboot status, the latest three essays, links to the section pages and the rotating quotes.
- `grammar.html`, `filmmakers.html`, `syllabus.html`, `lineage.html` and `reboot.html` are the section pages. Their bodies are edited by hand; `build_blog.py` fills their head tags, nav and footer between marker comments (`SEO`, `NAV`, `SITE-FOOT`, `SITE-LEGAL`), and the reboot ticker and ledger from `data_reboot.json`.
- `site.css` holds the styles shared by the front page and the section pages. Essay pages and the glossary keep their own styles inside `build_blog.py`.
- The nav and footer links are defined once, in `NAV_PAGES` and `MORE_PAGES` in `build_blog.py`.
- `posts-src/*.txt` are the essays, one file each, named `NN-slug.txt`.
- `build_blog.py` turns the essays into `blog/`. It also refreshes the homepage journal strip and SEO block, the section pages' shared parts, plus `sitemap.xml`, `feed.xml` and `robots.txt`.
- `images/agents/` holds the cast photos. `images/frames/` holds the essay and filmmaker images: an essay picks up `images/frames/<slug>.jpg` (1600x669, 2.39:1) automatically, for its card, its page header and its social preview. Every image is freely licensed or public domain from Wikimedia Commons, never a show still. Each one's credit lives in `images/frames/credits.json`, which `build_blog.py` uses to generate `credits.html`. `images/og.jpg` is the default social share image.

## Writing an essay

Each file starts with header lines, then a `---` line, then the body:

```
title: The essay title
date: 2026-10-19
tag: Cinematography
hue: 150
summary: One or two sentences used as the dek, the card text and the meta description.
---
Body paragraphs, separated by blank lines.

## Section heading

> A pull quote line.

Sources:
- [Label](https://example.com)
```

The body supports `## ` headings, `- ` lists, `> ` pull quotes, `*italic titles*` and `[links](https://...)`. House style: no em dashes or en dashes, every fact verified, sources listed at the end.

## Authorship

Only Claude Fable writes the actual prose on this site. Every word that ships to readers, the essays, the homepage copy, the section introductions, the syllabus and lineage notes, the error page, is drafted or edited by Fable. Other models may research, gather sources, fact-check, run `build_blog.py` and handle the plumbing, but the writing itself is Fable's. When a different model is driving a session, it delegates the writing pass to a Fable subagent rather than editing the copy directly.

The writing should sound as authentically human as possible. Keep the confident, literate voice, but avoid the tells of machine-written prose: the "it is not X, it is Y" antithesis on a loop, formula openers repeated across pieces, tidy triads, and endings that restate the thesis with a neat button. Vary sentence length, let some sentences be plain, and trim rather than pad.

After adding or editing an essay, rebuild:

```bash
python build_blog.py
```

Preview locally with `python -m http.server` and open http://127.0.0.1:8000/.

## The twice-weekly routine

A Claude Code cloud routine ("Mulder, It's Me: twice-weekly essay") runs Mondays and Thursdays at 15:00 UTC. Each run researches and drafts one new essay, has a Claude Fable subagent fact-check and edit it, rebuilds the site and pushes to `main`. It publishes nothing if the reviewer rejects the draft twice. Manage it at https://claude.ai/code/routines/trig_01YNXdLiGHLv8eQ8kFrsFw6D
