# Worklog

## 2026-07-10

**v1 build (1-hour timebox).** Interviewed via `/grill-me` against
`spec.md` to resolve the open technical decisions (shell, scheduling,
distribution, data storage), produced `PRD.md`, then built to it:

- Refactored `digest.py`'s fetch → filter → dedup loop into `core.py`,
  shared between the cron entrypoint and a new Flask app
- Migrated `config.yaml` (feeds + keywords) to flat JSON: `feeds.json`,
  `keywords.json`
- Built `app.py` — single main view (feeds, global keywords, matches),
  add/remove for both, manual "Refresh now", per-feed health badges
- Neo-brutalist UI: sharp borders, near-grayscale palette with light
  earth-tone accents
- Added a `summary` field to persisted matches (previously fetched for
  matching but discarded) so matches show links + summary, not just titles
- Fixed an XSS risk caught during build: feed-supplied text was briefly
  rendered with `| safe` in the template; switched to stripping HTML
  server-side before storing, since feed content is untrusted

**Post-build fixes, same day:**

- arXiv was drowning out every other feed. Added a per-feed `cap` (set to
  3 on arXiv) that re-ranks a feed's matches by TF-IDF cosine similarity
  against the keyword list on every refresh, keeping only the top N as a
  *running total* — not just capping new hits per refresh, which would
  still have grown unbounded over time
- Added 8 more feeds (Import AI, BAIR Blog, Interconnects, Latent Space,
  AI Snake Oil, The Gradient, Ahead of AI, AI Weekly), each verified live
  (real RSS, parses, has entries) before adding. Andrew Ng's "The Batch"
  has no discoverable RSS feed — skipped rather than scraped
- Summaries capped to 240 chars, matched keywords highlighted inline.
  Excerpt selection picks the 240-char window with the most keyword hits
  rather than always the first 240 chars, so the highlighted term is
  usually visible
- Fixed a UX bug: deleting a keyword/feed reloaded the page at the top
  instead of preserving scroll position; added a small vanilla-JS
  scroll-save/restore (sessionStorage, no dependencies)

**Repo setup:** initial commit, public GitHub repo. `feeds.json`,
`keywords.json`, and all runtime data files (`matches.json`, `seen.json`,
`status.json`) are gitignored — they contain the actual competitive-
research targets and scraped article text, not source. `feeds.example.json`
/ `keywords.example.json` ship instead as templates.

**Later same day:**

- Applied the per-feed `cap` (top-3 by TF-IDF relevance, running total) to
  every feed, not just arXiv — same drowning-out problem was starting on
  other high-volume feeds
- Checked each feed's actual RSS time range empirically (feedparser
  `published_parsed`, not something we control) — varies from same-day
  only (arXiv) to a ~12.7-year full archive (Ahead of AI/Raschka); the
  per-feed cap absorbs that variance rather than trying to filter by date
- Set up `launchd` to run `app.py` as a persistent background service
  (starts at login, restarts on crash) instead of a terminal/VSCode
  staying open — added `launchd/com.signaldigest.app.plist.example` to
  the repo as a template. Turned off Flask debug mode for this (`app.run`
  no longer passes `debug=True`) since a service left running
  indefinitely shouldn't expose Werkzeug's interactive debugger, even
  though it's localhost-only; tradeoff is code changes now need a manual
  `launchctl kickstart -k` instead of auto-reloading
