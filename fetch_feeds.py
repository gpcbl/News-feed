"""Combine several RSS/Atom feeds into one RSS feed and one JSON file.

Reads feeds.json, fetches every feed, removes duplicates, keeps recent items,
and writes:
  docs/feed.xml   - a single RSS 2.0 feed you can add to any reader
  docs/news.json  - the same items as JSON, easy for a web app to read

A feed that fails to load is skipped with a warning, so one broken source
never stops the whole run.
"""

import calendar
import json
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET
import html
import re
import socket

import feedparser

# Give up on any source that takes longer than 20 seconds to respond,
# so one slow site can't hang the whole run.
socket.setdefaulttimeout(20)

ROOT = Path(__file__).parent
CONFIG = ROOT / "feeds.json"
OUT_DIR = ROOT / "docs"

# Some news sites refuse requests that don't look like a browser.
feedparser.USER_AGENT = (
    "Mozilla/5.0 (compatible; personal-news-aggregator/1.0; +https://github.com)"
)


def clean_text(raw, limit=400):
    """Strip HTML tags and trim a summary to a readable length."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def item_date(entry):
    """Best available publish date as an aware UTC datetime, or None."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    return None


def story_key(title):
    """Normalize a headline so the same story from two feeds counts once.

    Google News titles end in " - Publisher", so that suffix is dropped.
    """
    title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title or "")
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def fetch_all(config):
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.get("max_age_days", 7))
    default_cap = config.get("per_feed_max", 20)
    seen = set()
    items = []
    failed = []

    for feed in config["feeds"]:
        cap = feed.get("max_items", default_cap)
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:  # timeouts, connection resets, etc.
            failed.append(f"{feed['name']} ({type(exc).__name__}: {exc})")
            continue
        status = getattr(parsed, "status", None)
        if parsed.bozo and not parsed.entries or (status and status >= 400):
            failed.append(f"{feed['name']} (status {status}, {parsed.get('bozo_exception', '')})")
            continue

        # Newest first, so the per-source cap keeps the freshest stories.
        entries = sorted(
            parsed.entries,
            key=lambda e: item_date(e) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        count = 0
        for entry in entries:
            if count >= cap:
                break
            link = (entry.get("link") or "").strip()
            title = clean_text(entry.get("title"), 200)
            keys = {k for k in (link, story_key(title)) if k}
            if not keys or keys & seen:
                continue
            published = item_date(entry)
            if published and published < cutoff:
                continue
            seen.update(keys)
            items.append({
                "title": title,
                "link": link,
                "summary": clean_text(entry.get("summary") or entry.get("description")),
                "source": feed["name"],
                "category": feed.get("category", "General"),
                "published": published.isoformat() if published else None,
            })
            count += 1
        print(f"  {feed['name']}: {count} items")

    # Newest first; items without a date go last.
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    return items[: config.get("max_items", 150)], failed


def write_rss(config, items, path):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = config["title"]
    ET.SubElement(channel, "link").text = config.get("link", "")
    ET.SubElement(channel, "description").text = config.get("description", "")
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))

    for i in items:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "title").text = i["title"]
        ET.SubElement(node, "link").text = i["link"]
        ET.SubElement(node, "guid", isPermaLink="true").text = i["link"]
        ET.SubElement(node, "description").text = i["summary"]
        ET.SubElement(node, "category").text = i["category"]
        ET.SubElement(node, "source", url=i["link"]).text = i["source"]
        if i["published"]:
            ET.SubElement(node, "pubDate").text = format_datetime(
                datetime.fromisoformat(i["published"])
            )

    ET.indent(rss)
    ET.ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)


def main():
    config = json.loads(CONFIG.read_text())
    OUT_DIR.mkdir(exist_ok=True)

    print(f"Fetching {len(config['feeds'])} feeds…")
    items, failed = fetch_all(config)

    write_rss(config, items, OUT_DIR / "feed.xml")
    (OUT_DIR / "news.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "categories": config.get("categories", []),
        "count": len(items),
        "items": items,
    }, indent=2, ensure_ascii=False))

    print(f"Wrote {len(items)} items to docs/feed.xml and docs/news.json")
    if failed:
        print("Skipped feeds that could not be loaded:")
        for f in failed:
            print(f"  - {f}")
    if not items:
        sys.exit("No items fetched from any feed; check the URLs in feeds.json.")


if __name__ == "__main__":
    main()
