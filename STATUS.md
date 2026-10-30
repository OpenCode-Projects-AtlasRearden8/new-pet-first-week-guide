# STATUS — new-pet-first-week-guide

Last verified: 2026-10-30 (build + full test suite passing)

## What was built

A kind, plain-English manual for the first week with a rescue cat or dog,
published as Markdown under `docs/` and compiled into a small static HTML
site by a dependency-free Python build script. Education only — every page
carries a "never veterinary advice" disclaimer.

**Content (all original goal topics covered):**

| Chapter | Topic |
| --- | --- |
| `docs/00-introduction.md` | Purpose, 3-3-3 rule, how to use the guide |
| `docs/01-before-you-bring-home.md` | Supply list, rescue paperwork and records |
| `docs/02-the-safe-room.md` | Setting up the quiet safe room, door discipline |
| `docs/03-day-one.md` | Arrival day step-by-step, what "normal" looks like |
| `docs/04-week-one-behavior.md` | Likely week-one behavior and what it means |
| `docs/05-feeding-and-routines.md` | Food transitions, feeding, daily routine anchors |
| `docs/06-first-vet-visit.md` | Paperwork kit to bring + full question checklist |
| `docs/07-introducing-family-and-pets.md` | Calm intros for kids, guests, existing pets |
| `docs/08-decoding-scary-behaviors.md` | What hissing/growling/freezing/hiding mean |
| `docs/09-call-the-vet-or-wait.md` | Education-only triage: go now / call today / wait |
| `docs/checklists/safe-room-checklist.md` | Printable safe-room checklist (checkbox list) |
| `docs/checklists/first-week-log-sheet.md` | Printable 7-day feed/water/potty/sleep/mood log |
| `docs/glossary.md` | Plain definitions of shelter/vet vocabulary |

**Infrastructure:**

- `scripts/build.py` — stdlib-only markdown-to-HTML converter + site
  generator (headings, lists incl. checkboxes and nesting, tables,
  blockquotes, bold/italic/code, `.md` link rewriting, prev/next nav,
  print-friendly CSS). `serve` subcommand starts a local-only preview server.
- `tests/test_build.py` — 28 tests: converter unit tests, full-site rebuild
  into a temp dir, internal-link resolution, raw-Markdown leak checks,
  per-page disclaimer check, live-serve smoke test, LICENSE/README checks,
  doc-file inventory, and intra-docs link validation.
- `README.md`, `LICENSE` (MIT, `Copyright (c) 2026 Asdale Dynamics, LLC`),
  `.gitignore` (site/, __pycache__).
- Pairs with the separate `free-pet-care-pack` printables — referenced in
  README and chapter 0.

## How to run it

```bash
python3 scripts/build.py                          # build the static site into site/
python3 scripts/build.py serve                    # build + serve at http://localhost:8377
python3 -m unittest discover -s tests -v          # run the test suite
```

Requires Python 3.9+ (no third-party packages). Built with Python 3.13.5.

## Verification results

- `python3 scripts/build.py` → "Built 14 pages (13 docs + index)" — success.
- `python3 -m unittest discover -s tests` → **28 tests, 0 failures**.
- Serve smoke test verified manually: `index.html`, `style.css`, and
  `checklists/safe-room-checklist.html` all return HTTP 200 on a local test
  run; the live-serve test also covers this in CI-style runs.
- All internal links in generated HTML resolve (tested, including from
  `checklists/` subdirectory pages and the index).
- No raw Markdown (`**`, `](`) leaks into generated HTML (tested).
- "Education only" disclaimer present on every generated page (tested).
- LICENSE contains the exact required copyright line (tested).
- Serve bug found and fixed during verification: `SimpleHTTPRequestHandler`
  resets `directory` in `__init__`, so the original class-attribute approach
  returned 404s; replaced with a proper subclass + `functools.partial`.

## Known gaps / future ideas

- Markdown coverage is a deliberate subset (no reference-style links, no
  nested tables, no footnotes, no syntax-highlighting in fenced code).
  Sufficient for this doc set; extend `scripts/build.py` if content grows.
- No sitemap.xml / meta-description per page; single-page deep-dive search
  is replaced by index cards. Fine at 14 pages.
- No images/illustrations (planned, optional).
- Log sheets and checklists print fine (print CSS included), but the
  fill-in form fields are blanks to hand-write; a future interactive
  (JS) version could save entries locally.
- Species-specific deep dives (kitten vs. senior-cat arrival plans, dog
  reactivity) are one chapter's worth of material, not dedicated guides.
- No per-page linting of Markdown beyond link/copyright/emoji tests;
  a basic prose style check could be added.
- The site is not published anywhere by this project; `site/` is
  gitignored and everything stays local-first.
