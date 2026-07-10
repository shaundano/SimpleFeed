"""Shared fetch/filter/dedup core for Signal Digest.

Used by both the cron entrypoint (digest.py) and the Flask app (app.py) so
there's exactly one copy of the fetch -> filter -> dedup logic.
"""

import json
import math
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import feedparser

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[a-z0-9]+")


def strip_html(text):
    """Strip tags and decode entities from feed-supplied HTML. Feed content
    is untrusted, so we never render it as raw HTML in the browser -- store
    plain text only."""
    return unescape(_TAG_RE.sub("", text or "")).strip()


def best_excerpt(text, keywords, length=240):
    """Pick the length-char window of text with the most matched-keyword
    hits, instead of always the first N chars -- a keyword that only
    appears in the title, or past the char cap, would otherwise show an
    excerpt with nothing highlighted in it."""
    text = text or ""
    if len(text) <= length:
        return text
    if not keywords:
        return text[:length].rsplit(" ", 1)[0] + "…"

    lower = text.lower()
    positions = []
    for kw in keywords:
        kw_l = kw.lower()
        start = 0
        while True:
            idx = lower.find(kw_l, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1

    if not positions:
        return text[:length].rsplit(" ", 1)[0] + "…"

    positions.sort()
    best_count, best_left = 0, 0
    left = 0
    for right in range(len(positions)):
        while positions[right] - positions[left] >= length:
            left += 1
        count = right - left + 1
        if count > best_count:
            best_count, best_left = count, left

    anchor = positions[best_left]
    window_start = max(0, anchor - 40)
    window_end = min(len(text), window_start + length)
    window_start = max(0, window_end - length)

    if window_start > 0:
        space = text.find(" ", window_start)
        if 0 <= space < window_start + 20:
            window_start = space + 1
    if window_end < len(text):
        space = text.rfind(" ", window_end - 20, window_end)
        if space != -1:
            window_end = space

    prefix = "…" if window_start > 0 else ""
    suffix = "…" if window_end < len(text) else ""
    return f"{prefix}{text[window_start:window_end]}{suffix}"


def _tokenize(text):
    return _WORD_RE.findall(text.lower())


def _tfidf_vectors(docs):
    """Pure-stdlib TF-IDF, no numpy/sklearn needed for a handful of docs
    per refresh. Returns one term->weight dict per doc, aligned with docs."""
    tokenized = [_tokenize(d) for d in docs]
    df = Counter()
    for tokens in tokenized:
        df.update(set(tokens))
    n_docs = len(docs)
    vectors = []
    for tokens in tokenized:
        tf = Counter(tokens)
        vec = {
            term: (count / len(tokens)) * (math.log((n_docs + 1) / (df[term] + 1)) + 1)
            for term, count in tf.items()
        }
        vectors.append(vec)
    return vectors


def _cosine(a, b):
    common = a.keys() & b.keys()
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_by_relevance(profile_text, candidates, text_fn, top_n):
    """Rank candidates by cosine similarity of text_fn(candidate) against
    profile_text (built from the feed's keyword list) and keep the top_n."""
    if len(candidates) <= top_n:
        return candidates
    docs = [profile_text] + [text_fn(c) for c in candidates]
    vectors = _tfidf_vectors(docs)
    profile_vec = vectors[0]
    scored = [(_cosine(profile_vec, vectors[i + 1]), c) for i, c in enumerate(candidates)]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in scored[:top_n]]

BASE_DIR = Path(__file__).parent
FEEDS_PATH = BASE_DIR / "feeds.json"
KEYWORDS_PATH = BASE_DIR / "keywords.json"
SEEN_PATH = BASE_DIR / "seen.json"
MATCHES_PATH = BASE_DIR / "matches.json"
STATUS_PATH = BASE_DIR / "status.json"


def _load(path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_feeds():
    return _load(FEEDS_PATH, [])


def save_feeds(feeds):
    _save(FEEDS_PATH, feeds)


def load_keywords():
    return _load(KEYWORDS_PATH, [])


def save_keywords(keywords):
    _save(KEYWORDS_PATH, keywords)


def load_seen():
    return set(_load(SEEN_PATH, []))


def save_seen(seen):
    _save(SEEN_PATH, sorted(seen))


def load_matches():
    return _load(MATCHES_PATH, [])


def save_matches(matches):
    _save(MATCHES_PATH, matches)


def load_status():
    return _load(STATUS_PATH, {})


def save_status(status):
    _save(STATUS_PATH, status)


def find_matches(text, keywords):
    """Case-insensitive substring match, so plurals/suffixes still match."""
    text = text.lower()
    return [kw for kw in keywords if kw.lower() in text]


def new_id():
    return uuid.uuid4().hex[:8]


def reconcile_matches(matches, feeds, global_keywords):
    """Re-check already-stored matches against the *current* feeds and
    keywords. Dropping a feed or a keyword used to leave its matches behind
    forever, because refresh only ever appended. Here we drop any match
    whose feed no longer exists or that no longer hits any current keyword,
    and recompute matched_keywords so highlights stay accurate."""
    feed_keywords_by_name = {
        f["name"]: global_keywords + f.get("keywords", []) for f in feeds
    }
    kept = []
    for m in matches:
        keywords = feed_keywords_by_name.get(m["source"])
        if keywords is None:
            continue  # feed was removed
        hits = find_matches(f"{m['title']} {m['summary']}", keywords)
        if not hits:
            continue  # no longer matches any current keyword
        m["matched_keywords"] = hits
        kept.append(m)
    return kept


def prune_matches():
    """Reconcile persisted matches against current feeds/keywords and save.
    Called after a feed/keyword is deleted so stale matches disappear
    immediately, without waiting for the next refresh."""
    matches = load_matches()
    pruned = reconcile_matches(matches, load_feeds(), [k["term"] for k in load_keywords()])
    save_matches(pruned)
    return pruned


def run_refresh():
    """Fetch all feeds, filter by keywords, dedup, persist matches + feed
    health. Returns the list of newly-added match dicts."""
    feeds = load_feeds()
    global_keywords = [k["term"] for k in load_keywords()]
    seen = load_seen()
    matches = reconcile_matches(load_matches(), feeds, global_keywords)
    status = load_status()

    new_results = []
    now = datetime.now(timezone.utc).isoformat()

    for feed in feeds:
        fid = feed["id"]
        name = feed["name"]
        url = feed["url"]
        feed_keywords = global_keywords + feed.get("keywords", [])

        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            status[fid] = {"last_fetched_at": now, "last_status": "error", "last_error": str(e)}
            continue

        if parsed.bozo and not parsed.entries:
            err = str(parsed.get("bozo_exception", "could not parse feed"))
            status[fid] = {"last_fetched_at": now, "last_status": "error", "last_error": err}
            continue

        status[fid] = {"last_fetched_at": now, "last_status": "ok", "last_error": None}

        feed_hits = []
        for entry in parsed.entries:
            uid = entry.get("id") or entry.get("link")
            if not uid or uid in seen:
                continue
            seen.add(uid)

            title = strip_html(entry.get("title", ""))
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            summary = strip_html(raw_summary)
            hits = find_matches(f"{title} {summary}", feed_keywords)

            if hits:
                feed_hits.append(
                    {
                        "item_id": uid,
                        "source": name,
                        "title": title,
                        "link": entry.get("link", ""),
                        "summary": summary,
                        "published_at": entry.get("published", ""),
                        "matched_keywords": hits,
                        "first_seen_at": now,
                    }
                )

        cap = feed.get("cap")
        if cap:
            # cap is a running total for this feed, not just this refresh's
            # new hits -- otherwise the feed still grows unbounded over
            # repeated refreshes. Re-rank existing + new together and keep
            # only the top `cap` overall.
            existing_for_feed = [m for m in matches if m["source"] == name]
            combined = existing_for_feed + feed_hits
            if len(combined) > cap:
                profile_text = " ".join(feed_keywords)
                combined = rank_by_relevance(
                    profile_text, combined, lambda m: f"{m['title']} {m['summary']}", cap
                )
            kept_ids = {m["item_id"] for m in combined}
            matches = [m for m in matches if m["source"] != name] + combined
            new_results.extend(m for m in feed_hits if m["item_id"] in kept_ids)
        else:
            matches.extend(feed_hits)
            new_results.extend(feed_hits)

    save_seen(seen)
    save_matches(matches)
    save_status(status)
    return new_results
