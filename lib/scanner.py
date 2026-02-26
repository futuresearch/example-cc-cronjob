"""Minimal Reddit scanner using the public JSON API.

Usage:
    python -m lib.scanner <subreddit>

Fetches the 25 most recent posts from a subreddit and outputs them as JSON.
No authentication required - uses Reddit's public .json endpoint.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

USER_AGENT = "community-scanner/0.1 (example bot)"


def fetch_subreddit(subreddit: str, limit: int = 25) -> list[dict]:
    """Fetch recent posts from a subreddit via the public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching r/{subreddit}: HTTP {e.code}", file=sys.stderr)
        return []
    except urllib.error.URLError as e:
        print(f"Error fetching r/{subreddit}: {e.reason}", file=sys.stderr)
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "title": post.get("title", ""),
            "selftext": post.get("selftext", ""),
            "author": post.get("author", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "created_utc": post.get("created_utc", 0),
            "subreddit": subreddit,
        })

    return posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch recent posts from a subreddit")
    parser.add_argument("subreddit", help="Subreddit name (without r/ prefix)")
    parser.add_argument("--limit", type=int, default=25, help="Number of posts to fetch")
    args = parser.parse_args()

    posts = fetch_subreddit(args.subreddit, limit=args.limit)
    print(json.dumps(posts, indent=2))
