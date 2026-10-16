# Mulder, It's Me

An unofficial film journal on The X-Files, served at https://mulderitsme.net from GitHub Pages. DNS is at Cloudflare, with records set to "DNS only".

## Layout

- `index.html` is the homepage: the WebGL UFO hero (three.js from jsDelivr), the journal strip, visual grammar, filmmakers, the viewing syllabus and the lineage timeline.
- `posts-src/*.txt` are the essays, one file each, named `NN-slug.txt`.
- `build_blog.py` turns the essays into `blog/`. It also refreshes the homepage journal strip and SEO block, plus `sitemap.xml`, `feed.xml` and `robots.txt`.
- `images/agents/` holds the cast photos from Wikimedia Commons (credits in `images/agents/CREDITS.md`). `images/og.jpg` is the social share image.

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

After adding or editing an essay, rebuild:

```bash
python build_blog.py
```

Preview locally with `python -m http.server` and open http://127.0.0.1:8000/.

## The twice-weekly routine

A Claude Code cloud routine ("Mulder, It's Me: twice-weekly essay") runs Mondays and Thursdays at 15:00 UTC. Each run researches and drafts one new essay, has a Claude Fable subagent fact-check and edit it, rebuilds the site and pushes to `main`. It publishes nothing if the reviewer rejects the draft twice. Manage it at https://claude.ai/code/routines/trig_01YNXdLiGHLv8eQ8kFrsFw6D
