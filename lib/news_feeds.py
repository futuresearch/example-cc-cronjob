"""RSS feed fetcher for news discovery.

Usage:
    python -m lib.news_feeds
    python -m lib.news_feeds --output-dir /tmp/news/
    python -m lib.news_feeds --feeds bbc_business techcrunch_ai

Fetches headlines from public RSS feeds and outputs them as JSON files.
No authentication required - uses standard RSS/Atom feeds.

Uses only stdlib (urllib, xml.etree.ElementTree, json).
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from xml.etree import ElementTree

USER_AGENT = "news-content-pipeline/0.1 (example bot; github.com/futuresearch/example-cc-cronjob)"

# Public RSS feeds - all freely accessible, no API keys needed
FEEDS = {
    "bbc_business": {
        "url": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "name": "BBC Business",
    },
    "techcrunch_ai": {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "name": "TechCrunch AI",
    },
    "hn_frontpage": {
        "url": "https://hnrss.org/frontpage",
        "name": "Hacker News Frontpage",
    },
    "ars_technica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "name": "Ars Technica",
    },
    "verge_ai": {
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "name": "The Verge AI",
    },
    "mit_tech_review": {
        "url": "https://www.technologyreview.com/feed/",
        "name": "MIT Technology Review",
    },
}

# Common XML namespaces in RSS/Atom feeds
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def fetch_feed(url: str) -> bytes | None:
    """Fetch raw XML from a feed URL."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"URL error fetching {url}: {e.reason}", file=sys.stderr)
        return None


def parse_rss_item(item: ElementTree.Element) -> dict:
    """Parse a single RSS <item> element."""
    return {
        "title": (item.findtext("title") or "").strip(),
        "link": (item.findtext("link") or "").strip(),
        "description": (item.findtext("description") or "").strip(),
        "published": (
            item.findtext("pubDate")
            or item.findtext(f"{{{NAMESPACES['dc']}}}date")
            or ""
        ).strip(),
    }


def parse_atom_entry(entry: ElementTree.Element) -> dict:
    """Parse a single Atom <entry> element."""
    link_el = entry.find(f"{{{NAMESPACES['atom']}}}link")
    link = link_el.get("href", "") if link_el is not None else ""

    return {
        "title": (entry.findtext(f"{{{NAMESPACES['atom']}}}title") or "").strip(),
        "link": link.strip(),
        "description": (
            entry.findtext(f"{{{NAMESPACES['atom']}}}summary")
            or entry.findtext(f"{{{NAMESPACES['atom']}}}content")
            or ""
        ).strip(),
        "published": (
            entry.findtext(f"{{{NAMESPACES['atom']}}}published")
            or entry.findtext(f"{{{NAMESPACES['atom']}}}updated")
            or ""
        ).strip(),
    }


def parse_feed(xml_bytes: bytes) -> list[dict]:
    """Parse RSS or Atom feed XML into a list of items."""
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as e:
        print(f"XML parse error: {e}", file=sys.stderr)
        return []

    items = []

    # Try RSS 2.0 format: <rss><channel><item>
    for item in root.iter("item"):
        parsed = parse_rss_item(item)
        if parsed["title"]:
            items.append(parsed)

    # Try Atom format: <feed><entry>
    if not items:
        for entry in root.iter(f"{{{NAMESPACES['atom']}}}entry"):
            parsed = parse_atom_entry(entry)
            if parsed["title"]:
                items.append(parsed)

    return items


def fetch_and_parse(feed_key: str, feed_config: dict) -> dict:
    """Fetch and parse a single feed, returning structured output."""
    xml = fetch_feed(feed_config["url"])
    if xml is None:
        return {
            "feed": feed_key,
            "name": feed_config["name"],
            "url": feed_config["url"],
            "status": "failed",
            "items": [],
        }

    items = parse_feed(xml)
    return {
        "feed": feed_key,
        "name": feed_config["name"],
        "url": feed_config["url"],
        "status": "ok",
        "item_count": len(items),
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch headlines from RSS feeds")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write JSON files (one per feed + manifest). If not set, prints to stdout.",
    )
    parser.add_argument(
        "--feeds",
        nargs="*",
        default=None,
        help=f"Feed keys to fetch (default: all). Available: {', '.join(FEEDS.keys())}",
    )
    args = parser.parse_args()

    feed_keys = args.feeds or list(FEEDS.keys())
    invalid = [k for k in feed_keys if k not in FEEDS]
    if invalid:
        print(f"Unknown feeds: {', '.join(invalid)}", file=sys.stderr)
        print(f"Available: {', '.join(FEEDS.keys())}", file=sys.stderr)
        sys.exit(1)

    results = []
    for key in feed_keys:
        print(f"Fetching {FEEDS[key]['name']}...", file=sys.stderr)
        result = fetch_and_parse(key, FEEDS[key])
        results.append(result)
        print(
            f"  {result['status']}: {result.get('item_count', 0)} items",
            file=sys.stderr,
        )

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

        # Write individual feed files
        for result in results:
            path = os.path.join(args.output_dir, f"{result['feed']}.json")
            with open(path, "w") as f:
                json.dump(result, f, indent=2)

        # Write manifest
        manifest = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "feeds": [
                {
                    "feed": r["feed"],
                    "name": r["name"],
                    "status": r["status"],
                    "item_count": r.get("item_count", 0),
                    "file": f"{r['feed']}.json",
                }
                for r in results
            ],
            "total_items": sum(r.get("item_count", 0) for r in results),
        }
        manifest_path = os.path.join(args.output_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(
            f"\nWrote {len(results)} feeds ({manifest['total_items']} total items) to {args.output_dir}",
            file=sys.stderr,
        )
    else:
        # Print all results to stdout
        output = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "feeds": results,
            "total_items": sum(r.get("item_count", 0) for r in results),
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
