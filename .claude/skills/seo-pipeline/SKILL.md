---
name: seo-pipeline
description: Run the SEO optimization pipeline. Collects Google Search Console data, analyzes pages with LLM judgment, proposes improvements, and creates a PR. Use when asked to "run seo", "seo pipeline", or "optimize seo".
---

# SEO Pipeline

Automated SEO optimization pipeline. Collects Google Search Console data, runs per-page analysis with an LLM agent, and proposes title/description improvements as a pull request. The human reviews the PR and applies changes manually.

**Key principle: propose, don't implement.** The pipeline never modifies your site files directly. It writes a report with proposed changes. You read the PR and decide what to apply.

## MCP Configuration

This skill requires the Google Search Console MCP server. Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "google-search-console": {
      "command": "uvx",
      "args": ["mcp-server-gsc"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/path/to/your/service-account-credentials.json"
      }
    }
  }
}
```

You'll need Google Search Console API credentials. See https://github.com/AminForou/mcp-gsc for setup.

## Configuration

- **Domain**: `sc-domain:example.com` (replace with your GSC property)
- **Content directory**: Where your markdown/MDX files live (edit `CONTENT_DIR` in `lib/seo_prepare.py`)
- **Page categories**: Which pages are blog posts, docs, landing pages (edit `PAGE_CATEGORIES` in `lib/seo_prepare.py`)

## Architecture

```
Phase 1: Collect GSC Data (MCP)  ->  Phase 2: Prepare Inputs (Python)
    ->  Phase 3: Analyze Pages (agents)  ->  Phase 4: Record Changes
    ->  Phase 5: Report + PR
```

---

## Phase 1: Collect GSC Data

### Date Range

Last 7 days inclusive. Running on 2026-01-23 means start=2026-01-17, end=2026-01-23.

### 1a. Create Run Directory

```bash
mkdir -p data/seo/runs/{date}/raw
```

### 1b. All Pages Performance

```
mcp__google-search-console__search_analytics:
  siteUrl: "sc-domain:example.com"
  startDate: "{start}"
  endDate: "{end}"
  dimensions: "page"
  rowLimit: 500
```

Write to `data/seo/runs/{date}/raw/all-pages.json`

### 1c. Query+Page Mapping (the key data)

```
mcp__google-search-console__search_analytics:
  siteUrl: "sc-domain:example.com"
  startDate: "{start}"
  endDate: "{end}"
  dimensions: "query,page"
  rowLimit: 25000
```

Write to `data/seo/runs/{date}/raw/page-queries.json`

### 1d. Record Metadata

Write `data/seo/runs/{date}/raw/metadata.json` with `collected_at`, `date_range`, and `domain`.

---

## Phase 2: Prepare Per-Page Inputs

```bash
python -m lib.seo_prepare --date {date}
```

Produces one JSON file per page at `data/seo/runs/{date}/pages/{slug}.json` containing: current GSC metrics, search queries, previous run's metrics, computed diff, and experiment history.

The experiment history is the feedback loop. When you implement a proposed title change, the next run measures whether clicks improved, regressed, or stayed flat. This feeds back into the analyzer.

---

## Phase 3: Analyze All Pages

Run the `seo-page-analyzer` agent on every page, including pages with 0 impressions.

### Batching

Spawn agents in parallel, up to 5 at a time:

```
Task (subagent_type: seo-page-analyzer): "Analyze page data/seo/runs/{date}/pages/blog-dedup-guide.json"
Task (subagent_type: seo-page-analyzer): "Analyze page data/seo/runs/{date}/pages/docs-getting-started.json"
... (up to 5)
```

Wait for each batch before starting the next. Continue until all pages are analyzed.

---

## Phase 4: Record Proposed Changes

Do NOT modify site files. Record proposed changes to `data/seo/changes/{date}.json`:

```json
{
  "recorded_at": "ISO timestamp",
  "run_id": "run-{date}",
  "changes": [
    {
      "slug": "blog-dedup-guide",
      "field": "title",
      "old_value": "Deduplication Guide",
      "new_value": "How to Deduplicate CSV Data: A Practical Guide",
      "reasoning": "Top query has 450 impressions at position 8.2 but only 3 clicks.",
      "data_at_change": { "clicks": 3, "impressions": 450, "ctr": 0.007, "position": 8.2 }
    }
  ]
}
```

The `data_at_change` snapshot is critical -- the next run compares current metrics against it to determine experiment outcome.

---

## Phase 5: Report + PR

Write `data/seo/reports/{date}-seo-report.md`:

```markdown
# SEO Report - {date}

GSC data: {start} to {end}

## All Pages

| Slug | Impr (D) | Clicks (D) | CTR (D) | Position (D) |
| ---- | -------- | ---------- | ------- | ------------- |
| blog-dedup-guide | 450 (+50) | 3 (+1) | 0.7% (+0.1%) | 8.2 (-0.3) |
| ... | ... | ... | ... | ... |

## Proposed Changes

Changes below are proposals only - apply manually to your site.

**blog-dedup-guide** - title
- Was: "Deduplication Guide"
- Proposed: "How to Deduplicate CSV Data: A Practical Guide"
- Why: Top query "how to deduplicate csv" has 450 impressions at position 8.2 but only 3 clicks.
```

Order by impressions descending. Pages with 0 impressions at the bottom.

Create branch `seo/{date}`, commit all run data, push, create PR titled "SEO report: {date}".

---

## The Experiment History Feedback Loop

1. **Run N**: Pipeline proposes a title change. Human applies it.
2. **Run N+1**: `seo_prepare.py` loads the change log, compares current GSC metrics against `data_at_change`, computes outcome:
   - **improved**: CTR up >20% or position improved >1 rank
   - **regressed**: CTR down >20% or position worsened >1 rank
   - **neutral**: No significant change
   - **pending**: Less than 7 days since change
3. The `seo-page-analyzer` sees this history and adjusts: repeat what worked, try different approaches when things regressed, wait when pending experiments show positive signals.

---

## Error Recovery

- **GSC API fails**: Log failure in report, don't fail the entire run.
- **Agent fails on a page**: Log it, continue with remaining pages.
- **No suggestions**: Report "no changes proposed this week."

Never fail the entire skill. Always produce a report.

---

## Data Flow

```
GSC MCP  ->  data/seo/runs/{date}/raw/  ->  Python (lib/seo_prepare.py)
  ->  data/seo/runs/{date}/pages/{slug}.json  ->  Agents (seo-page-analyzer x N)
  ->  data/seo/changes/{date}.json  ->  data/seo/reports/{date}-seo-report.md  ->  PR
```
