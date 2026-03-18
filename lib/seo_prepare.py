"""Prepare SEO data for analysis agents.

Takes raw GSC data and produces per-page input files for seo-page-analyzer agents.
Computes metrics, week-over-week diffs, and loads experiment history.

Usage:
    python -m lib.seo_prepare --date 2026-01-23
    python -m lib.seo_prepare --date 2026-01-23 --dry-run

No external dependencies -- stdlib only (json, pathlib, argparse).
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

# Configuration: edit these for your site
DOMAIN = "example.com"  # Must match GSC page URLs
CONTENT_DIR = Path("content")  # Where your .md/.mdx files live
PAGE_CATEGORIES: dict[str, str] = {}  # slug -> category (blog, docs, landing)
DATA_DIR = Path("data/seo")


def _load(path: Path) -> list | dict:
    if not path.exists(): return []
    try: return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError): return []


def _normalize(data: list | dict) -> list[dict]:
    """Flatten GSC MCP response ({rows: [{keys, clicks, ...}]}) into dicts."""
    rows = data.get("rows", data) if isinstance(data, dict) else data if isinstance(data, list) else []
    out = []
    for r in rows:
        if "keys" not in r: out.append(r); continue
        e = {"url": r["keys"][-1]} if r["keys"] else {}
        if len(r["keys"]) >= 2: e["query"] = r["keys"][0]
        for f in ("clicks", "impressions", "ctr", "position"): e[f] = r.get(f, 0)
        out.append(e)
    return out


def _index(rows: list[dict]) -> dict:
    """Build URL -> metrics dict or URL -> [query dicts] lookup."""
    out: dict = {}
    for r in rows:
        url = r.get("url", "")
        if "query" in r: out.setdefault(url, []).append(r)
        else: out[url] = {k: r.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
    for v in out.values():
        if isinstance(v, list): v.sort(key=lambda x: x.get("impressions", 0), reverse=True)
    return out


def _find(slug, metrics, queries):
    for u in (f"https://{DOMAIN}/{slug}/", f"https://{DOMAIN}/{slug}",
              f"https://www.{DOMAIN}/{slug}/", f"https://www.{DOMAIN}/{slug}"):
        m, q = metrics.get(u), queries.get(u, [])
        if m or q: return m, q
    return None, []


def _diff(cm, cq, pm, pq):
    if not pm and not pq: return None
    c, p = cm or {}, pm or {}
    pmap, cmap = {q["query"]: q for q in pq}, {q["query"]: q for q in cq}
    return {
        "clicks_delta": c.get("clicks", 0) - p.get("clicks", 0),
        "impressions_delta": c.get("impressions", 0) - p.get("impressions", 0),
        "ctr_delta": round(c.get("ctr", 0) - p.get("ctr", 0), 4),
        "position_delta": round((p.get("position") or 0) - (c.get("position") or 0), 2),
        "queries_gained": sorted([{"query": q, **cmap[q]} for q in set(cmap) - set(pmap)],
                                 key=lambda x: x["impressions"], reverse=True)[:20],
        "queries_lost": sorted([{"query": q, **pmap[q]} for q in set(pmap) - set(cmap)],
                                key=lambda x: x["impressions"], reverse=True)[:20],
    }


def _history(slug, current, date):
    """Load experiment outcomes from data/seo/changes/*.json."""
    cdir = DATA_DIR / "changes"
    if not cdir.exists(): return []
    hist = []
    for f in sorted(cdir.glob("*.json")):
        data = _load(f)
        if not isinstance(data, dict): continue
        for ch in data.get("changes", []):
            if ch.get("slug") != slug: continue
            exp = f.stem
            try: days = (datetime.strptime(date, "%Y-%m-%d") - datetime.strptime(exp, "%Y-%m-%d")).days
            except (ValueError, TypeError): days = 0
            before = ch.get("data_at_change", {})
            after, outcome = None, "pending"
            if days >= 7 and current:
                after = {k: current.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
                bc, ac = before.get("ctr", 0), after.get("ctr", 0)
                cp = ((ac - bc) / bc * 100) if bc else 0
                pd = (before.get("position") or 100) - (after.get("position") or 100)
                outcome = "improved" if cp > 20 or pd > 1 else "regressed" if cp < -20 or pd < -1 else "neutral"
            hist.append({"experiment_date": exp, "days_since": days, "change_type": ch.get("field"),
                         "old_value": ch.get("old_value"), "new_value": ch.get("new_value"),
                         "data_before": before or None, "data_after": after, "outcome": outcome})
    return hist


def prepare(date: str, dry_run: bool = False) -> dict:
    raw = DATA_DIR / "runs" / date / "raw"
    pdir = DATA_DIR / "runs" / date / "pages"
    pages = _normalize(_load(raw / "all-pages.json"))
    qdata = _normalize(_load(raw / "page-queries.json"))
    if not pages and not qdata:
        print(f"Error: no raw data in {raw}"); return {"error": "missing_files"}

    mi, qi = _index(pages), _index(qdata)
    # Previous run
    rdir = DATA_DIR / "runs"
    prev = sorted([d.name for d in rdir.iterdir() if d.is_dir() and d.name < date], reverse=True) if rdir.exists() else []
    pd = prev[0] if prev else None
    pm, pq = {}, {}
    if pd:
        pr = DATA_DIR / "runs" / pd / "raw"
        pm, pq = _index(_normalize(_load(pr / "all-pages.json"))), _index(_normalize(_load(pr / "page-queries.json")))

    # Build inventory
    inv, slugs = [], set()
    if CONTENT_DIR.exists():
        for ext in ("*.md", "*.mdx"):
            for f in sorted(CONTENT_DIR.glob(ext)):
                s = f.stem; slugs.add(s)
                inv.append({"slug": s, "url": f"https://{DOMAIN}/{s}/",
                            "category": PAGE_CATEGORIES.get(s, "other"), "title": "", "description": ""})
    for url in mi:
        s = url.rstrip("/").split("/")[-1]
        if s and s not in slugs:
            slugs.add(s)
            inv.append({"slug": s, "url": url, "category": PAGE_CATEGORIES.get(s, "other"), "title": "", "description": ""})

    if not dry_run: pdir.mkdir(parents=True, exist_ok=True)
    meta = _load(raw / "metadata.json")
    dr = meta.get("date_range", {}) if isinstance(meta, dict) else {}

    for p in inv:
        s = p["slug"]
        m, q = _find(s, mi, qi); prm, prq = _find(s, pm, pq)
        out = {"slug": s, "url": p["url"], "category": p["category"],
               "current_metadata": {"title": p["title"], "description": p["description"]},
               "gsc_current": {"date_range": dr, "clicks": (m or {}).get("clicks", 0),
                               "impressions": (m or {}).get("impressions", 0), "ctr": (m or {}).get("ctr", 0),
                               "position": (m or {}).get("position"), "in_gsc": m is not None, "queries": q[:30]},
               "gsc_previous": {"clicks": prm.get("clicks", 0), "impressions": prm.get("impressions", 0),
                                "ctr": prm.get("ctr", 0), "position": prm.get("position")} if prm else None,
               "gsc_diff": _diff(m, q, prm, prq), "experiment_history": _history(s, m, date)}
        if not dry_run: (pdir / f"{s}.json").write_text(json.dumps(out, indent=2))

    print(f"Prepared {len(inv)} pages for {date}" + (f" (prev: {pd})" if pd else ""))
    return {"date": date, "pages": len(inv), "previous_run": pd, "at": datetime.now(UTC).isoformat()}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Prepare SEO data for analysis agents")
    p.add_argument("--date", required=True, help="Run date (YYYY-MM-DD)")
    p.add_argument("--dry-run", action="store_true", help="Show what would be created")
    a = p.parse_args()
    print(json.dumps(prepare(a.date, a.dry_run), indent=2))
