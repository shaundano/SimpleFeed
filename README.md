# Signal Digest

A self-hosted, keyword-filtered RSS digest. Point it at a handful of RSS/Atom
feeds, give it a keyword list, and it surfaces only the entries that match —
title, source, matched keywords, and a short excerpt, newest first. No
scraping, no LLM calls, no accounts, no cloud sync: it's a single local Flask
app backed by flat JSON files.

Built to track signal on a specific research niche without wading through
SEO-polluted search results or someone else's curation. See
[`docs/spec.md`](docs/spec.md) for the original problem statement and
[`docs/PRD.md`](docs/PRD.md) for the v1 design decisions.

## Quick start

```bash
pip install -r requirements.txt
cp feeds.example.json feeds.json
cp keywords.example.json keywords.json
# edit feeds.json / keywords.json with your own feeds and keywords
python3 app.py
```

Open `http://127.0.0.1:5050`. From there you can add/remove feeds, add/remove
global keywords, and hit "Refresh now" to fetch.

## Running it in the background (launchd, macOS)

For daily use you probably don't want a terminal window open just to keep
the web UI alive. `launchd` will run it as a background service that starts
at login and restarts itself if it ever crashes:

```bash
mkdir -p logs
cp launchd/com.signaldigest.app.plist.example ~/Library/LaunchAgents/com.signaldigest.app.plist
# edit that copy: replace /path/to/python3 and /path/to/SimpleFeed with your
# actual paths (`which python3` for the former)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.signaldigest.app.plist
```

Then bookmark `http://127.0.0.1:5050` and it's always there when you click it.

- Logs: `logs/app.log` / `logs/app.err.log`
- Restart after a code change (auto-reload is off in this mode):
  `launchctl kickstart -k gui/$(id -u)/com.signaldigest.app`
- Stop: `launchctl bootout gui/$(id -u)/com.signaldigest.app`

## How it works

- `core.py` — shared fetch → filter → dedup logic (fetches each feed,
  matches title+summary against your keywords, dedups against `seen.json`,
  persists results to `matches.json`)
- `app.py` — Flask web UI, single main view, wraps `core.py`
- `digest.py` — thin cron/launchd entrypoint, calls the same `core.py` logic
  for scheduled (non-interactive) runs

A feed can optionally set `"cap": N` in `feeds.json` to cap how many of its
matches are kept at once — useful for high-volume feeds (e.g. arXiv) that
would otherwise drown out lower-volume sources. When capped, matches are
ranked by TF-IDF cosine similarity against your keyword list and only the
top N are kept, re-ranked on every refresh.

## Scheduling

The app itself doesn't schedule anything — run `python3 digest.py` on a
cron/launchd timer to fetch on a schedule, and open the web UI whenever you
want to triage what it found. Both read/write the same JSON files.

## Data files (gitignored, local only)

`feeds.json`, `keywords.json`, `matches.json`, `seen.json`, and
`status.json` are your personal state — not committed. Templates are
provided as `feeds.example.json` / `keywords.example.json`.

## Docs

- [`docs/spec.md`](docs/spec.md) — original problem/scope spec
- [`docs/PRD.md`](docs/PRD.md) — v1 design decisions and architecture
- [`docs/WORKLOG.md`](docs/WORKLOG.md) — build log
