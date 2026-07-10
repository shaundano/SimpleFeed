#!/usr/bin/env python3
"""
digest.py -- cron/launchd entrypoint for Signal Digest.

Runs the shared fetch -> filter -> dedup cycle (core.run_refresh) and
prints a summary. Feeds/keywords are managed via the web app (app.py) and
persisted to feeds.json / keywords.json; matches accumulate in
matches.json for both the cron run and the web app to read.

Usage:
    python3 digest.py

Run daily (or weekly) via cron / launchd / Task Scheduler.
"""

import core


def main():
    new_results = core.run_refresh()

    if not new_results:
        print("No new matches this run.")
        return

    print(f"{len(new_results)} new match(es):\n")
    for r in new_results:
        print(f"- {r['title']} ({r['source']})")
        print(f"  matched: {', '.join(r['matched_keywords'])}")
        print(f"  {r['link']}\n")


if __name__ == "__main__":
    main()
