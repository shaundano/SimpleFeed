# Signal Digest — Project Spec (draft v0.1)

> Working title only. Rename freely — this doc is about scope, not branding.

## Context

Built out of a competitive-research need: tracking "world-action model" companies
and research (both model-builders and data-infrastructure players) for a robotics
foundation-model spinout. Google search is too SEO-polluted and too slow to index
stealth launches. Crunchbase's newsletter is funding-news-only and not filterable
for free. The fix was a self-owned keyword filter over a small set of high-signal
RSS feeds (arXiv categories, Crunchbase News, two niche Substacks written by
credible practitioners) instead of relying on someone else's curation.

## Problem

Existing solution (CLI script) works but has friction:
- Editing `config.yaml` by hand to add/remove feeds or tune keywords
- Output is flat markdown files in a `digests/` folder — fine, but no single
  place to browse history, no read/unread state beyond the dedup file
- No visibility into whether a feed silently broke (wrong URL, feed format
  changed, site blocked the request) without reading stdout logs

## Goals (v1)

- [ ] Add/remove/edit feeds without touching a config file by hand
- [ ] Add/remove/edit keywords without touching a config file by hand
- [ ] View digest entries in a readable list (not raw markdown), newest first
- [ ] Manual "refresh now" action
- [ ] Feed health visibility — flag a feed if the last fetch failed
- [ ] Keep the core logic (fetch → filter → dedup) as close to the already-tested
      Python script as possible; this is a UI wrapper, not a rewrite

## Explicit non-goals (v1)

- Multi-user / accounts / auth — this is a single-user local tool
- Cloud sync or hosted version
- Mobile app
- Push notifications
- Summarization or scoring of articles (no LLM calls in the fetch pipeline)
- Anything beyond RSS/Atom as a source type (no scraping, no APIs requiring keys)

## Why a desktop app at all (the thing to interrogate first)

The CLI + markdown version already solves the core problem end to end and was
working before this doc was written. The honest justification for a GUI is
narrow: (1) editing YAML by hand to manage feeds/keywords is annoying enough
to cause drop-off, and (2) a single scrollable "everything I've seen" view beats
hunting through dated markdown files. If those two frictions aren't real after
a few weeks of daily use of the CLI version, this app isn't worth building.
Worth a gut-check before scoping further.

## Current state (already built, tested offline)

- `signal_digest.py` — fetches feeds via `feedparser`, keyword-matches title +
  summary (case-insensitive substring, so plurals/suffixes match), dedups
  against `seen.json`, writes `digests/<date>.md`
- `config.yaml` — feed list (`name`, `url`) and keyword list
- No database, no server, no scheduling — cron/launchd runs it externally
- Not yet tested against live feeds in this environment (sandbox network
  couldn't reach arxiv.org / crunchbase.com / substack.com); logic verified
  against mock RSS only

## Proposed data model

- `feeds`: `{ id, name, url, last_fetched_at, last_status: ok | error, last_error }`
- `keywords`: `{ id, term }`
- `seen_items`: `{ item_id (link or guid) }` — dedup only, no content stored
- `matches`: `{ item_id, source, title, link, published_at, matched_keywords[], first_seen_at }`

This is a straightforward move from two flat files to SQLite — small enough
that it shouldn't be controversial, but flagging it as a decision, not a given.

## Open technical decisions (flag these for review, don't assume answers)

1. **Shell**: Electron, Tauri, a pure-Python GUI (e.g. PySide), or just a local
   web server + browser tab? Tradeoff is packaging weight vs. dev speed vs.
   "is this actually a desktop app or a localhost site with extra steps."
2. **Scheduling**: keep relying on OS-level cron/launchd (simple, invisible to
   the app, breaks silently) vs. an in-app background scheduler (more moving
   parts, but the app can show "last checked 4 min ago").
3. **Distribution**: is "clone the repo and run it" sufficient, or does
   "keep on GitHub" imply packaged installers/releases? Affects how much
   packaging tooling is worth adding for a single-user tool.
4. **Where filtering logic lives**: stays in Python as-is (app just wraps it),
   or gets ported into whatever language the shell ends up in? Porting adds
   risk for no functional gain unless the shell choice forces it.

## Success criteria

- Opening the app once a day and triaging new matches takes under 2 minutes
- Adding a new feed or keyword takes under 10 seconds and doesn't require
  opening a text editor
- A broken feed is visible in the app within one refresh cycle, not silently
  dropped

## Risks / assumptions

- Feed URLs and formats can change without notice (arXiv, Substack, and
  Crunchbase have all changed feed infrastructure before) — health-check
  visibility (a stated goal) is the mitigation, not a guarantee
- Keyword list requires ongoing tuning; false negatives (missed signal) are
  worse than false positives (extra reading) for this use case, so matching
  should stay permissive by default
- Real scope-creep risk: this is a personal research tool wrapped in "desktop
  app" framing — worth being deliberate that v1 stays smaller than the
  ambition implied by "app on GitHub"