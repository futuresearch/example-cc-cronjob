---
name: community-scanner
description: Scan Reddit communities for people with data problems, classify opportunities, and create a PR with results.
---

# Community Scanner

Scan subreddits for people struggling with data problems, classify the opportunities, and create a PR with a report.

This is a simplified version of a production pipeline that scans 18+ community sources daily. It demonstrates the pattern: Python does the mechanical fetching, Claude does the judgment.

## Configuration

Subreddits to scan (edit this list to target your communities):

- r/dataengineering
- r/excel
- r/salesforce

## Phase 1: Scan

Run the Python scanner for each subreddit:

```bash
python -m lib.scanner dataengineering
python -m lib.scanner excel
python -m lib.scanner salesforce
```

Each call outputs JSON to stdout with recent posts from that subreddit. Collect all results into a single list. If a subreddit fails (rate limited, unavailable), log it and continue with the others.

Deduplicate against `data/seen.txt` - skip any URL that already appears in that file. Append new URLs to `data/seen.txt`.

After deduplication, if no new posts remain, skip to Phase 3 with an empty report.

## Phase 2: Classify

For each post from Phase 1, evaluate it by answering these questions:

1. **problem_type**: Is this person describing a real data problem, or is this a discussion/announcement/career question?
2. **semantic_needed**: Does this problem require semantic understanding (fuzzy matching, entity resolution, judgment), or would exact matching/VLOOKUP/SQL solve it?
3. **scale**: How many rows/records? (quote if stated, "unknown" if not)
4. **tools_tried**: What have they already tried?
5. **solvable**: Could our tools plausibly help? Be honest - most posts are not a fit.

Assign a score from 1 to 5:

| Score | Meaning |
|-------|---------|
| 1 | Not a data problem, or trivially solvable with existing tools |
| 2 | Data problem but exact matching would work fine |
| 3 | Possible fit - semantic understanding might help |
| 4 | Good fit - clear need for semantic matching or AI-powered processing |
| 5 | Excellent fit - perfect use case, high visibility, helpful response would get upvoted |

Important: At no point should you write a Python script for classification. Read the posts and think about them.

## Phase 3: Report

Write a markdown report to `data/reports/scan-<date>.md`:

```markdown
# Community Scan Report - <date>

## Summary
- Posts scanned: N
- After dedup: N
- Score 4-5: N
- Score 1-2: N

## Top Opportunities (Score 4-5)

### [Score X] <title>
- **URL:** <url>
- **Subreddit:** r/<subreddit>
- **Problem:** <one-line summary>
- **Why it's a fit:** <brief explanation>

## All Classifications

| Score | Subreddit | Title | URL |
|-------|-----------|-------|-----|
| ... | ... | ... | ... |
```

If no posts were found or all scored 1-2, the report should still be created noting that.

## Phase 4: PR

1. Create a branch named `scan/<date>`
2. Commit the report and updated `data/seen.txt`
3. Push and create a PR titled "Community scan: <date>"

The PR is the output. A human opens it, reads the report, and decides what to do with the opportunities.
