"""Tests for the New Pet First Week Guide build.

Run with:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
README = ROOT / "README.md"
LICENSE = ROOT / "LICENSE"

# Load scripts/build.py as a module regardless of the package layout.
_spec = importlib.util.spec_from_file_location("petguide_build", ROOT / "scripts" / "build.py")
build_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("petguide_build", build_mod)
_spec.loader.exec_module(build_mod)


def build_to_tmp() -> tuple[Path, list]:
    tmp = Path(tempfile.mkdtemp(prefix="petguide-site-"))
    pages = build_mod.build(out_dir=tmp)
    return tmp, pages


class TestMarkdownConverter(unittest.TestCase):
    def render(self, md: str) -> str:
        return build_mod.render_markdown(md)

    def test_headings(self):
        out = self.render("# Hello\n\n## Sub")
        self.assertIn("<h1", out)
        self.assertIn("<h2", out)
        self.assertIn("Hello", out)

    def test_bold_italic_code(self):
        out = self.render("This is **bold**, *soft*, and `code`.")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>soft</em>", out)
        self.assertIn("<code>code</code>", out)

    def test_link_and_md_rewrite(self):
        out = self.render("Read [the guide](chapter.md) first.")
        self.assertIn('href="chapter.html"', out)
        self.assertIn(">the guide</a>", out)

    def test_unordered_list(self):
        out = self.render("- one\n- two")
        self.assertEqual(out.count("<li>"), 2)
        self.assertIn("<ul>", out)

    def test_ordered_list_with_nested(self):
        out = self.render("1. step one\n2. step two\n   - nested a\n   - nested b")
        self.assertIn("<ol>", out)
        self.assertIn("<ul>", out)
        self.assertIn("nested a", out)

    def test_checkbox_list(self):
        out = self.render("- [ ] unchecked\n- [x] done")
        self.assertIn('type="checkbox"', out)
        self.assertIn(" checked", out)

    def test_table(self):
        out = self.render("| A | B |\n| --- | --- |\n| 1 | 2 |")
        self.assertIn("<table>", out)
        self.assertIn("<th>A</th>", out)
        self.assertIn("<td>2</td>", out)

    def test_blockquote(self):
        out = self.render("> quote line")
        self.assertIn("<blockquote>", out)
        self.assertIn("quote line", out)

    def test_html_escaping(self):
        out = self.render("a < b & c")
        self.assertIn("&lt;", out)
        self.assertIn("&amp;", out)
        self.assertNotIn("<b ", out)

    def test_paragraph_merges_lines(self):
        out = self.render("first half\nsecond half")
        self.assertIn("first half second half", out)
        self.assertEqual(out.count("<p>"), 1)

    def test_inline_markdown_left_untouched_in_html_output(self):
        out = self.render("plain **bold**")
        self.assertIn("<strong>", out)
        self.assertNotIn("**", out)


class TestGeneratedSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.pages = build_to_tmp()
        cls.site = cls.tmp

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_index_exists_and_lists_pages(self):
        index = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertIn("New Pet First Week Guide", index)
        for page in self.pages:
            self.assertIn(page.href, index)

    def test_every_doc_has_a_page(self):
        docs = {p.relative_to(DOCS).with_suffix(".html").as_posix() for p in DOCS.rglob("*.md")}
        built = {p.href for p in self.pages}
        self.assertEqual(docs, built)

    def test_expected_pages_present(self):
        hrefs = [p.href for p in self.pages]
        for expected in (
            "00-introduction.html",
            "02-the-safe-room.html",
            "checklists/safe-room-checklist.html",
            "checklists/first-week-log-sheet.html",
            "glossary.html",
        ):
            self.assertIn(expected, hrefs)

    def test_page_titles_extracted(self):
        titles = {p.page_title for p in self.pages}
        self.assertIn("00 · Introduction", titles)
        self.assertIn("Safe-Room Checklist", titles)

    def test_no_raw_markdown_leaks_into_html(self):
        for page in self.pages:
            html = (self.site / page.href).read_text(encoding="utf-8")
            body = html.split("<main")[1].split("</main>")[0]
            self.assertNotIn("**", body, page.href)
            self.assertNotIn("](", body, page.href)
            self.assertLessEqual(len(re.findall(r"^#{1,6} ", body, re.M)), 0, page.href)

    def test_internal_links_resolve(self):
        checked = 0
        for page in self.pages:
            html = (self.site / page.href).read_text(encoding="utf-8")
            dir_of = (self.site / page.href).parent
            for target in re.findall(r'(?:href|src)="([^"]+)"', html):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                checked += 1
                resolved = (dir_of / target).resolve()
                self.assertTrue(resolved.exists(), f"{page.href} -> {target}")
        self.assertGreater(checked, 10)

    def test_no_md_links_left_in_html(self):
        for page in self.pages:
            html = (self.site / page.href).read_text(encoding="utf-8")
            self.assertNotIn('.md"', html, page.href)

    def test_style_sheet_written(self):
        css = (self.site / "style.css").read_text(encoding="utf-8")
        self.assertIn("@media print", css)

    def test_disclaimer_on_every_page(self):
        for page in self.pages:
            html = (self.site / page.href).read_text(encoding="utf-8")
            self.assertIn("Education only", html, page.href)

    def test_can_serve_site(self):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from functools import partial

        handler = partial(build_mod.SimpleHTTPRequestHandler, directory=str(self.site))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/index.html", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("New Pet First Week Guide", resp.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()


class TestFrontMatterSources(unittest.TestCase):
    def test_license_copyright_line_exact(self):
        text = LICENSE.read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", text)

    def test_readme_credits_llc_and_links_docs(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", text)
        self.assertIn("scripts/build.py", text)

    def test_readme_doc_links_resolve(self):
        text = README.read_text(encoding="utf-8")
        for target in re.findall(r'\]\((docs/[^)]+)\)', text):
            self.assertTrue((ROOT / target).exists(), target)

    def test_docs_disclaim_edical_scope(self):
        joined = "\n".join(p.read_text(encoding="utf-8") for p in sorted(DOCS.rglob("*.md")))
        self.assertIn("never veterinary advice", joined)

    def test_expected_doc_files_exist(self):
        names = {p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.md")}
        for expected in (
            "00-introduction.md",
            "01-before-you-bring-home.md",
            "02-the-safe-room.md",
            "03-day-one.md",
            "04-week-one-behavior.md",
            "05-feeding-and-routines.md",
            "06-first-vet-visit.md",
            "07-introducing-family-and-pets.md",
            "08-decoding-scary-behaviors.md",
            "09-call-the-vet-or-wait.md",
            "checklists/safe-room-checklist.md",
            "checklists/first-week-log-sheet.md",
            "glossary.md",
        ):
            self.assertIn(expected, names)

    def test_md_internal_links_resolve(self):
        broken = []
        for md_path in DOCS.rglob("*.md"):
            text = md_path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#h]+\.md[^)]*)\)", text):
                resolved = (md_path.parent / target.split("#")[0]).resolve()
                if not resolved.exists():
                    broken.append(f"{md_path.relative_to(DOCS)} -> {target}")
        self.assertEqual(broken, [])

    def test_no_emoji_in_docs(self):
        pattern = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]")
        offenders = []
        for md_path in DOCS.rglob("*.md"):
            for match in pattern.finditer(md_path.read_text(encoding="utf-8")):
                offenders.append(f"{md_path.name}: {match.group(0)!r}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
