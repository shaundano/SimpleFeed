# Signal Digest — PRD v1 (1-hour build)

> Resolves the open decisions flagged in `spec.md` via grill-me. Supersedes
> spec.md's "Proposed data model" and "Open technical decisions" sections;
> everything else in spec.md (Context, Problem, Goals, Non-goals, Success
> criteria, Risks) still applies.

## Context

Same as `spec.md`: competitive-research tool for tracking "world-action
model" companies/research, currently a working CLI script (`digest.py`) with
config-file and markdown-file friction. This PRD scopes the smallest GUI
wrapper that removes that friction, buildable in 1 hour.

## Decisions resolved

| Decision | Answer | Why |
|---|---|---|
| Shell | Local Python web server (Flask) + browser tab | No packaging/build step; reuses `digest.py` in-process; fastest path to a working CRUD UI in 1hr |
| Scheduling | Keep OS cron/launchd | App stays a passive viewer/editor + on-demand refresh; matches the "open once a day" usage model in the success criteria |
| Distribution | Clone repo + run | Single-user tool; packaging would consume the whole timebox |
| Filtering logic location | Stays in Python, unchanged | Settled by shell choice — no cross-language bridge needed |
| Data storage | Flat JSON files, not SQLite | Same order of complexity as today's flat files; SQLite's schema/migration work doesn't fit in 1hr alongside CRUD + health checks |
| Read/unread state | Out of scope for v1 | Named in spec's Problem narrative but never made it into the Goals checklist — cut to protect timebox |
| Visual design | Neo-brutalist, muted/near-grayscale + light earth-tone accents (Physical Intelligence–inspired) | User preference |
| Keyword scope | Global list + optional per-feed overrides | User wants both; global list matches everywhere, a feed can add extra keywords on top. Flagged as the first thing to cut if the hour runs short — see Scope below |
| Layout | Single main view, not separate pages per resource | User asked for "really simple": add-feed, keyword management, and matches all live on one page (`/`), not a multi-page nav |
| Content stored | Links + summary only, no full article body | Matches `digest.py`'s existing `summary` field (already fetched for keyword matching, just wasn't persisted to output) |

## Scope (v1, 1 hour)

**Core (build first):**
- [ ] Single main view (`/`) with three stacked sections: feeds, global keywords, matches
- [ ] Feeds section: list (name, URL, ok/error status badge), delete button, add-feed form (name + URL)
- [ ] Global keywords section: list, delete button, add-keyword form
- [ ] Matches section: newest first — title, source, matched keyword(s), link, **summary**, published date
- [ ] "Refresh now" button — runs fetch → filter → dedup synchronously, then redisplays the page
- [ ] Feed health badge — ok/error per feed, with `last_error` shown on the error state
- [ ] `digest.py`'s fetch/filter/dedup loop refactored into an importable module shared by the existing cron invocation and the new web app (no duplicated logic)

**Stretch (cut first if the hour runs short):**
- [ ] Per-feed keyword overrides — optional keyword field on the add-feed form; matching for that feed = global list ∪ its own list. If cut, ship with global-only keywords and note it as the first v1.1 follow-up.

## Non-goals (unchanged from spec.md, plus this PRD's cuts)

Multi-user/auth, cloud sync, mobile, push notifications, LLM summarization/
scoring, non-RSS sources, packaged installers, in-app scheduler — **plus**,
newly cut for the 1hr budget: SQLite, read/unread tracking.

## Data model (flat JSON — replaces spec.md's SQLite proposal)

- `feeds.json` — `[{id, name, url, keywords: []}]` (replaces `config.yaml`'s
  feed list; `keywords` is the per-feed override list, empty by default —
  stretch scope, see above)
- `keywords.json` — `[{id, term}]`, global list (replaces `config.yaml`'s
  keyword list)
- `seen.json` — `[item_id]`, unchanged — dedup only, no content stored
- `matches.json` — `[{item_id, source, title, link, summary, published_at, matched_keywords[], first_seen_at}]`
  (replaces `digests/*.md`; `summary` is the feed's own summary/description
  text, not fetched article content — no scraping)
- `status.json` — `{feed_id: {last_fetched_at, last_status: "ok"|"error", last_error}}` (new — feed health, doesn't exist today)

Matching per feed = global `keywords.json` list ∪ that feed's own
`keywords` array (if per-feed overrides are built).

## Architecture

- Extract `digest.py`'s core loop (load config → fetch → match → dedup →
  write results) into functions importable from a new `app.py`. Persist
  `entry.get("summary")` into `matches.json` (currently fetched for
  matching but discarded after).
- `app.py` (Flask) routes, all rendering the single main view:
  - `GET /` — full page: feeds section, global keywords section, matches
    list (newest first)
  - `POST /feeds`, `POST /feeds/<id>/delete`
  - `POST /keywords`, `POST /keywords/<id>/delete`
  - `POST /refresh` — runs the fetch cycle synchronously, redirects to `/`
- Cron/launchd keeps invoking the same shared module on its existing
  schedule — this PRD does not change how the scheduled run is triggered,
  only what it reads/writes (JSON instead of YAML/markdown).

## Visual design direction

- Neo-brutalist: sharp edges, visible borders/dividers, bold type, minimal
  shadow/decoration
- Near-grayscale palette with light earth-tone accents; reserve the one
  saturated color for the "error" status badge so broken feeds are
  impossible to miss
- Dense, scannable list layout — supports the "<2 min daily triage"
  success criterion

## Success criteria

Unchanged from `spec.md`: daily triage under 2 minutes; add a feed/keyword
in under 10 seconds without opening a text editor; a broken feed visible
within one refresh cycle.

## Risks / known limitations carried into v1

- Flat JSON with no DB means a concurrent cron run + web app write could
  race. Acceptable for a single-user local tool; revisit if it becomes a
  real problem.
- Keyword edits are prospective only — since `seen.json` only stores dedup
  IDs (not content) for non-matches, adding a keyword won't retroactively
  surface past entries that didn't match the old list. This is inherent to
  the existing dedup design, not a new limitation introduced here.
- This is the thinnest defensible v1 under a literal 1-hour timebox.
  SQLite, read/unread, packaging, and in-app scheduling are explicit
  v1.1+ candidates — worth revisiting only if the friction the spec
  gut-checks for (`spec.md`, "Why a desktop app at all") turns out to be
  real after a few weeks of daily use.
