# Mulder, It's Me

An unofficial X-Files fan site, built as plain static files for GitHub Pages.

- `index.html` is the homepage: the WebGL hero (three.js from jsDelivr), the flashlight office, dossiers, the conspiracy board, case files, and the belief gauge.
- `posts-src/*.txt` are the blog posts. Each one has a few header lines (`title`, `date`, `tag`, `icon`, `summary`), then a `---` line, then the body. The body supports paragraphs, `## ` headings, `- ` lists and `[links](https://...)`.
- `build_blog.py` turns the posts into `blog/` and refreshes the "From the blog" strip on the homepage. Run it after adding or editing a post:

```bash
python build_blog.py
```

Preview locally with `python -m http.server` and open http://127.0.0.1:8000/.

To use a custom domain, add a `CNAME` file containing the domain, then set it under the repo's Settings > Pages.
