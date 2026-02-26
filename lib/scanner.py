"""Reddit scanner using the public JSON API.

Usage:
    python -m lib.scanner <subreddit>
    python -m lib.scanner <subreddit> --limit 50
    python -m lib.scanner <subreddit> --with-comments

Fetches recent posts from a subreddit and outputs them as JSON.
No authentication required - uses Reddit's public .json endpoint.

With --with-comments, also fetches the top comments for each post
(one additional request per post - be mindful of rate limits).
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

USER_AGENT = "community-scanner/0.1 (example bot; github.com/futuresearch/example-cc-cronjob)"


def fetch_json(url: str) -> dict | None:
    """Fetch JSON from a URL with error handling."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} fetching {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"URL error fetching {url}: {e.reason}", file=sys.stderr)
        return None


def fetch_comments(permalink: str, limit: int = 10) -> list[dict]:
    """Fetch top comments for a post via its permalink."""
    url = f"https://www.reddit.com{permalink}.json?limit={limit}&sort=top"
    data = fetch_json(url)
    if not data or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child.get("data", {})
        comments.append({
            "author": c.get("author", ""),
            "body": c.get("body", ""),
            "score": c.get("score", 0),
        })

    return comments


def fetch_subreddit(
    subreddit: str,
    limit: int = 25,
    with_comments: bool = False,
) -> list[dict]:
    """Fetch recent posts from a subreddit via the public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    data = fetch_json(url)
    if not data:
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        permalink = post.get("permalink", "")

        entry = {
            "url": f"https://www.reddit.com{permalink}",
            "title": post.get("title", ""),
            "selftext": post.get("selftext", ""),
            "author": post.get("author", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "created_utc": post.get("created_utc", 0),
            "subreddit": subreddit,
        }

        if with_comments and post.get("num_comments", 0) > 0:
            time.sleep(1)  # Rate limit: 1 request per second
            entry["comments"] = fetch_comments(permalink)

        posts.append(entry)

    return posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch recent posts from a subreddit")
    parser.add_argument("subreddit", help="Subreddit name (without r/ prefix)")
    parser.add_argument("--limit", type=int, default=25, help="Number of posts to fetch")
    parser.add_argument(
        "--with-comments",
        action="store_true",
        help="Also fetch top comments for each post (slower, one extra request per post)",
    )
    args = parser.parse_args()

    posts = fetch_subreddit(args.subreddit, limit=args.limit, with_comments=args.with_comments)
    print(json.dumps(posts, indent=2))
