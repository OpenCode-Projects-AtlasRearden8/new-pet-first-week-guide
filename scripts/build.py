#!/usr/bin/env python3
"""Build the New Pet First Week Guide static site from docs/.

Dependency-free: uses only the Python standard library.

Usage:
    python3 scripts/build.py          # build site/ (or --out DIR)
    python3 scripts/build.py serve    # build, then serve locally
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
import shutil
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"
TITLE = "New Pet First Week Guide"
TAGLINE = "A kind manual for a rescue cat or dog's first seven days"
DISCLAIMER = "Education only — never veterinary advice. When in doubt, call your vet."
COPYRIGHT = "Copyright (c) 2026 Asdale Dynamics, LLC"

STYLE = """\
:root {
  --ink: #2b2823;
  --muted: #6b6459;
  --paper: #fdfbf7;
  --accent: #7a5c3e;
  --line: #e6dfd3;
  --code-bg: #f2eee5;
}
* { box-sizing: border-box; }
html { font-size: 17px; }
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.65;
  color: var(--ink);
  background: var(--paper);
}
.wrap { max-width: 46rem; margin: 0 auto; padding: 0 1.25rem; }
a { color: var(--accent); }
h1, h2, h3, h4 { line-height: 1.25; }
h1 { font-size: 1.9rem; margin: 0 0 .8rem; }
h2 { font-size: 1.4rem; margin: 2rem 0 .5rem; border-bottom: 1px solid var(--line); padding-bottom: .25rem; }
h3 { font-size: 1.1rem; margin: 1.5rem 0 .4rem; }
p { margin: .75rem 0; }
ul, ol { padding-left: 1.4rem; }
li { margin: .3rem 0; }
code {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: .85em;
  background: var(--code-bg);
  padding: .1em .35em;
  border-radius: 4px;
}
pre { background: var(--code-bg); padding: .75rem 1rem; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote {
  margin: 1rem 0;
  padding: .5rem 1rem;
  border-left: 4px solid var(--accent);
  background: #f7f3ea;
  border-radius: 0 6px 6px 0;
}
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }
th, td { border: 1px solid var(--line); padding: .45rem .6rem; text-align: left; vertical-align: top; }
th { background: #f7f3ea; }
hr { border: none; border-top: 1px solid var(--line); margin: 2rem 0; }

.site-header {
  border-bottom: 1px solid var(--line);
  background: #fff;
}
.site-header .wrap { display: flex; flex-wrap: wrap; align-items: baseline; gap: .4rem 1rem; padding: .9rem 1.25rem; }
.home { font-weight: bold; text-decoration: none; color: var(--ink); font-size: 1.05rem; }
.tagline { color: var(--muted); font-style: italic; font-size: .85rem; }

.pagenav {
  display: flex; justify-content: space-between; gap: 1rem;
  font-size: .9rem; margin-top: 3rem; padding-top: .8rem;
  border-top: 1px solid var(--line);
}

.hero h1 { margin-top: 2rem; }
.hero .lede { font-size: 1.1rem; color: var(--muted); font-style: italic; }
.cards { list-style: none; padding: 0; margin: 1.5rem 0; }
.cards li { border: 1px solid var(--line); border-radius: 8px; padding: .7rem 1rem; margin: .6rem 0; background: #fff; }
.cards a { font-weight: bold; text-decoration: none; }
.cards .desc { display: block; color: var(--muted); font-size: .9rem; margin-top: .15rem; }

.site-footer {
  margin-top: 3rem; padding: 1.2rem 0 2rem;
  border-top: 1px solid var(--line);
  color: var(--muted); font-size: .85rem;
}
.notice { font-style: italic; }

@media print {
  .site-header, .pagenav, .site-footer { display: none; }
  body { font-size: 12pt; background: #fff; }
  a { color: inherit; text-decoration: none; }
  .cards li { break-inside: avoid; }
}
"""


# --------------------------------------------------------------------------
# Inline markdown -> HTML (on a single line, after HTML escaping)
# --------------------------------------------------------------------------

def esc(text: str) -> str:
    return html_mod.escape(text, quote=True)


def inline(text: str) -> str:
    """Convert inline markdown (links, code, bold, italic) to HTML."""
    text = esc(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # links, rewriting relative .md targets to .html
    def _link(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        if target.endswith(".md"):
            target = target[:-3] + ".html"
        return f'<a href="{target}">{label}</a>'
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def heading_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"h-{slug}" if slug else "h"


# --------------------------------------------------------------------------
# Block-level markdown -> HTML
# --------------------------------------------------------------------------

LIST_RE = re.compile(r"^(\s*)(?:([-*])|(\d+)[.)])\s+(.*)$")
CHECK_RE = re.compile(r"^\[([ xX])\]\s+(.*)$")


class _Item:
    __slots__ = ("indent", "ordered", "check", "text", "children")

    def __init__(self, indent: int, ordered: bool, check: str | None, text: str):
        self.indent = indent
        self.ordered = ordered
        self.check = check
        self.text = text
        self.children: list[_Item] = []


def _collect_list_items(lines: list[str], start: int) -> tuple[list[_Item], int]:
    """Gather a run of list items (with nesting and continuations)."""
    items: list[_Item] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            # A blank line inside a list is tolerated only when the next
            # non-blank line is itself a list item; otherwise the list ends.
            peek = i + 1
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek < len(lines) and LIST_RE.match(lines[peek]):
                i = peek
                continue
            break
        m = LIST_RE.match(line)
        if m:
            indent, bullet, num, rest = m.groups()
            check = None
            cm = CHECK_RE.match(rest)
            if cm:
                check = cm.group(1)
                rest = cm.group(2)
            indent_width = len(indent) if bullet else len(indent) + 2
            items.append(_Item(indent_width, bool(num), check, rest.strip()))
            i += 1
        elif line[:1].isspace() and items:
            # continuation of the previous item's text
            items[-1].text += " " + line.strip()
            i += 1
        else:
            break
    return items, i


def _build_tree(items: list[_Item]) -> list[_Item]:
    """Nest flat items by indent into top-level roots with children."""
    roots: list[_Item] = []
    stack: list[_Item] = []
    for item in items:
        while stack and item.indent <= stack[-1].indent:
            stack.pop()
        if stack:
            stack[-1].children.append(item)
        else:
            roots.append(item)
        stack.append(item)
    return roots


def _render_item_run(run: list[_Item]) -> str:
    ordered = run[0].ordered
    tag = "ol" if ordered else "ul"
    out = [f"<{tag}>"]
    for it in run:
        text = _render_tree(it.children)
        inner = inline(it.text)
        if it.check is not None:
            check = " checked" if it.check.lower() == "x" else ""
            inner = f'<input type="checkbox" disabled{check}> {inner}'
        out.append(f"<li>{inner}{text}</li>")
    out.append(f"</{tag}>")
    return "".join(out)


def _render_tree(items: list[_Item]) -> str:
    if not items:
        return ""
    roots = _build_tree(items)
    out = []
    run: list[_Item] = []
    for it in roots:
        # keep runs of the same list type together
        if run and run[-1].ordered != it.ordered:
            out.append(_render_item_run(run))
            run = []
        run.append(it)
    if run:
        out.append(_render_item_run(run))
    return "".join(out)


def _table_html(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header, *body = rows
    out = ['<table>', "<thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in header]
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            out += [f"<td>{inline(c)}</td>" for c in row]
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "".join(out)


def render_markdown(md: str) -> str:
    """Convert a Markdown document (subset) to an HTML fragment."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # blank
        if not stripped:
            i += 1
            continue

        # fenced code block
        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            out.append(f"<pre><code>{esc(chr(10).join(buf))}</code></pre>")
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            out.append(f'<h{level} id="{heading_id(text)}">{inline(text)}</h{level}>')
            i += 1
            continue

        # horizontal rule
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            out.append("<hr>")
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            out.append(f"<blockquote>{render_markdown(chr(10).join(buf))}</blockquote>")
            continue

        # table: current line and next line are both pipe rows
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            rows = []
            rows.append([c.strip() for c in stripped.strip("|").split("|")])
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(_table_html(rows))
            continue

        # list (unordered, ordered, checkbox)
        if LIST_RE.match(line):
            items, i = _collect_list_items(lines, i)
            out.append(_render_tree(items))
            continue

        # paragraph: gather until blank line or an obvious block start
        buf = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (not nxt
                    or re.match(r"^(#{1,6}\s|\s*[-*]\s|\s*\d+[.)]|>|```|\|)", lines[i])
                    or re.match(r"^(-{3,}|\*{3,})$", nxt)):
                break
            buf.append(nxt)
            i += 1
        out.append(f"<p>{inline(' '.join(buf))}</p>")

    return "\n".join(out)


# --------------------------------------------------------------------------
# Site assembly
# --------------------------------------------------------------------------

def docs_files() -> list[Path]:
    files = sorted(DOCS.rglob("*.md"))
    return files


def page_title(md_text: str, path: Path, order_index: int | None) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def description(md_text: str) -> str:
    """First non-heading paragraph, trimmed at a word boundary, for cards."""
    lines = md_text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            rest = lines[idx + 1:]
            for candidate in rest:
                c = candidate.strip()
                if c:
                    if len(c) > 160:
                        c = " ".join(c[:160].split(" ")[:-1]) + " ..."
                    return c
    return ""


PAGE_SHELL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {site}</title>
<link rel="stylesheet" href="{rel}style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="home" href="{rel}index.html">{site}</a>
    <span class="tagline">{tagline}</span>
  </div>
</header>
<main class="wrap">
{content}
{pagenav}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p class="notice">{disclaimer}</p>
    <p>{copyright} · {credit}</p>
  </div>
</footer>
</body>
</html>
"""


def pagenav_html(rel: str, prev_page, next_page) -> str:
    parts = []
    if prev_page:
        parts.append(f'<a href="{rel}{prev_page.href}">&larr; {esc(prev_page.page_title)}</a>')
    else:
        parts.append('<span></span>')
    parts.append(f'<a href="{rel}index.html">Contents</a>')
    if next_page:
        parts.append(f'<a href="{rel}{next_page.href}">{esc(next_page.page_title)} &rarr;</a>')
    else:
        parts.append('<span></span>')
    return f'<nav class="pagenav">{"".join(parts)}</nav>'


class Page:
    def __init__(self, href: str, md_path: Path, title: str, desc: str, html: str):
        self.href = href  # relative to site root, e.g. "guide.html" or "checklists/x.html"
        self.md_path = md_path
        self.page_title = title
        self.desc = desc
        self.html = html


def build(out_dir: Path = SITE) -> list[Page]:
    out_dir = out_dir.resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "style.css").write_text(STYLE, encoding="utf-8")

    pages: list[Page] = []
    for md_path in docs_files():
        md_text = md_path.read_text(encoding="utf-8")
        rel_md = md_path.relative_to(DOCS)
        href = str(rel_md.with_suffix(".html")).replace("\\", "/")
        title = page_title(md_text, md_path, None)
        desc = description(md_text)
        body = render_markdown(md_text)
        pages.append(Page(href, md_path, title, desc, body))

    for idx, page in enumerate(pages):
        depth = page.href.count("/")
        rel = "../" * depth
        prev_page = pages[idx - 1] if idx > 0 else None
        next_page = pages[idx + 1] if idx + 1 < len(pages) else None
        nav = pagenav_html(rel, prev_page, next_page)
        html_out = PAGE_SHELL.format(
            title=esc(page.page_title),
            site=esc(TITLE),
            tagline=esc(TAGLINE),
            rel=rel,
            content=page.html,
            pagenav=nav,
            disclaimer=esc(DISCLAIMER),
            copyright=esc(COPYRIGHT),
            credit='Site by <a href="https://dylanasdale.github.io">Asdale Dynamics, LLC</a>',
        )
        target = out_dir / page.href
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_out, encoding="utf-8")

    # index
    cards = []
    for page in pages:
        cards.append(
            f'<li><a href="{esc(page.href)}">{esc(page.page_title)}</a>'
            f'<span class="desc">{esc(page.desc)}</span></li>'
        )
    index_body = f"""\
<section class="hero">
  <h1>{esc(TITLE)}</h1>
  <p class="lede">{esc(TAGLINE)}</p>
</section>
<p>Bringing home a rescue cat or dog is a big transition — for both of you.
This guide walks through the first seven days, one calm step at a time:
the safe room, first-week behavior, food and routines, the first vet visit,
calm introductions, decoding scary behaviors, and knowing when to call the
vet versus wait.</p>
<p><strong>{esc(DISCLAIMER)}</strong></p>
<h2>Contents</h2>
<ul class="cards">
{''.join(cards)}
</ul>
"""
    index_html = PAGE_SHELL.format(
        title="Home",
        site=esc(TITLE),
        tagline=esc(TAGLINE),
        rel="",
        content=index_body,
        pagenav="",
        disclaimer=esc(DISCLAIMER),
        copyright=esc(COPYRIGHT),
        credit='Site by <a href="https://dylanasdale.github.io">Asdale Dynamics, LLC</a>',
    )
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")
    return pages


def serve(out_dir: Path = SITE, port: int = 8377, open_browser: bool = False) -> None:
    target_dir = str(out_dir.resolve())

    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=target_dir, **kwargs)

    url = f"http://localhost:{port}/"
    print(f"Serving {target_dir} at {url} (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(SITE), help="output directory (default: site/)")
    parser.add_argument("cmd", nargs="?", choices=["build", "serve"], default="build")
    parser.add_argument("--port", type=int, default=8377)
    parser.add_argument("--open", action="store_true", help="open the browser when serving")
    args = parser.parse_args()
    out_dir = Path(args.out)
    pages = build(out_dir)
    print(f"Built {len(pages) + 1} pages ({len(pages)} docs + index) into {out_dir}")
    if args.cmd == "serve":
        serve(out_dir, port=args.port, open_browser=args.open)


if __name__ == "__main__":
    main()
