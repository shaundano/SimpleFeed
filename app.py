"""Signal Digest -- local web UI. Run with: python3 app.py, then open
http://127.0.0.1:5050
"""

import re

from flask import Flask, redirect, render_template, request, url_for
from markupsafe import Markup, escape

import core

app = Flask(__name__)

SUMMARY_CHAR_CAP = 240


def highlight_keywords(text, keywords):
    """Escape text, then wrap matched keyword occurrences in <mark>. Text
    is escaped first so this is safe to mark `| safe` in the template even
    though the underlying summary came from an untrusted feed."""
    text = text or ""
    escaped = str(escape(text))
    terms = sorted({k for k in (keywords or []) if k}, key=len, reverse=True)
    if not terms:
        return Markup(escaped)
    pattern = re.compile("|".join(re.escape(k) for k in terms), re.IGNORECASE)
    return Markup(pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped))


app.jinja_env.filters["highlight"] = highlight_keywords
app.jinja_env.filters["best_excerpt"] = core.best_excerpt


@app.route("/")
def index():
    feeds = core.load_feeds()
    keywords = core.load_keywords()
    matches = sorted(core.load_matches(), key=lambda m: m["first_seen_at"], reverse=True)
    status = core.load_status()
    return render_template(
        "index.html", feeds=feeds, keywords=keywords, matches=matches, status=status
    )


@app.route("/feeds", methods=["POST"])
def add_feed():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    raw_keywords = request.form.get("keywords", "").strip()
    feed_keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()] if raw_keywords else []
    if name and url:
        feeds = core.load_feeds()
        feeds.append({"id": core.new_id(), "name": name, "url": url, "keywords": feed_keywords})
        core.save_feeds(feeds)
    return redirect(url_for("index"))


@app.route("/feeds/<feed_id>/delete", methods=["POST"])
def delete_feed(feed_id):
    feeds = [f for f in core.load_feeds() if f["id"] != feed_id]
    core.save_feeds(feeds)
    return redirect(url_for("index"))


@app.route("/keywords", methods=["POST"])
def add_keyword():
    term = request.form.get("term", "").strip()
    if term:
        keywords = core.load_keywords()
        keywords.append({"id": core.new_id(), "term": term})
        core.save_keywords(keywords)
    return redirect(url_for("index"))


@app.route("/keywords/<keyword_id>/delete", methods=["POST"])
def delete_keyword(keyword_id):
    keywords = [k for k in core.load_keywords() if k["id"] != keyword_id]
    core.save_keywords(keywords)
    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh():
    core.run_refresh()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(port=5050, debug=True)
