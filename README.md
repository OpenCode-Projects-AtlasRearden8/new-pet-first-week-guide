# New Pet First Week Guide

A kind, plain-English manual for bringing home a rescue cat or dog and surviving —
gently — the first seven days together.

Written the way a friend would explain it: step by step, never condescending,
and never pretending this replaces your veterinarian.

**This project is education only. It is never veterinary advice.**
If your animal is in real distress, call your vet or an emergency animal clinic.

## What's inside

The manual lives as Markdown in [`docs/`](docs/), and a build script turns it
into a small static HTML site you can open locally — no server, no account,
no data leaving your machine.

| Doc | What it covers |
| --- | --- |
| [Introduction](docs/00-introduction.md) | What to expect from this guide, and the 3-3-3 rule |
| [Before you bring them home](docs/01-before-you-bring-home.md) | Supplies with a rescue's paperwork and history |
| [The quiet safe room](docs/02-the-safe-room.md) | Setting up one calm space your new pet can call their own |
| [Day one](docs/03-day-one.md) | The first hours: arrivals, hiding, no pressure |
| [Week-one behavior](docs/04-week-one-behavior.md) | What's normal (and what isn't) in the first seven days |
| [Feeding and routines](docs/05-feeding-and-routines.md) | Food transitions, schedules, sleep, and predictability |
| [The first vet visit](docs/06-first-vet-visit.md) | Paperwork to carry, questions to ask, what to expect |
| [Introducing family](docs/07-introducing-family-and-pets.md) | Kids, partners, guests, and existing pets — calmly |
| [Decoding scary behaviors](docs/08-decoding-scary-behaviors.md) | What hiding, hissing, growling, and freezing really mean |
| [Call the vet — or wait?](docs/09-call-the-vet-or-wait.md) | A calm triage guide for the "something's off" moments |
| [Safe-room checklist](docs/checklists/safe-room-checklist.md) | Printable room-by-room checklist |
| [First-week log sheet](docs/checklists/first-week-log-sheet.md) | Track food, water, potty, sleep, and mood for 7 days |
| [Glossary](docs/glossary.md) | Plain definitions for the words shelters and vets use |

## How to build the site

You need Python 3.9+ only — no packages to install.

```bash
python3 scripts/build.py
```

This generates a static site in `site/`. Open it with:

```bash
python3 scripts/build.py serve   # optional tiny local server
# or just open site/index.html in your browser
```

## How to run the tests

```bash
python3 -m unittest discover -s tests -v
```

The tests verify the build: every doc converts, links resolve, and the
generated site is complete.

## Design choices

- **Local-first.** Everything runs on your machine. No tracking, no uploads.
- **Kind, not clinical.** Rescue pets are overwhelmed, not broken.
- **Print-friendly pages** so checklists and the log sheet can go on a fridge.

## Who made this

Built by [Asdale Dynamics, LLC](https://dylanasdale.github.io) — Dylan Asdale's
project for beginner-friendly guides and practical tools, explained like a
friend would. This guide pairs with the separate **free-pet-care-pack**
printables project: the pack gives you forms and trackers, this guide explains
how to use them in week one.

## License

MIT — see [LICENSE](LICENSE).
