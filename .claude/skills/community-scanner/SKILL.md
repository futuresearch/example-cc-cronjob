---
name: community-scanner
description: Scan Reddit communities for people with data problems, classify opportunities, propose responses, and create a PR with results.
---

# Community Scanner

Scan subreddits for people struggling with data problems, classify opportunities with a structured rubric, draft responses for the best ones, and create a PR with a report.

This is a simplified version of a production pipeline that scans 18 community sources daily. It demonstrates the pattern: Python does the mechanical fetching, Claude does the judgment. In production, each phase fans out to parallel subagents. Here, everything runs in a single process to keep it simple.

## How It Works

```
Phase 1: Scan
  └── Python scanner fetches posts from each subreddit
       ↓ dedup against seen.txt, initial filtering
Phase 2: Classify
  └── Answer 13 structured questions per post, assign 1-5 score
       ↓ filter to score 4-5
Phase 3: Propose
  └── Select strategy, draft forum response for each high-scoring post
       ↓
Phase 4: Report
  └── Markdown report with metrics, top opportunities, draft responses
       ↓
Phase 5: PR
  └── Branch, commit, push, open PR
```

The output is a pull request. A human opens it, reads the report, and decides what to do.

## Configuration

Subreddits to scan (edit this list to target your communities):

- r/dataengineering
- r/excel
- r/salesforce

Products we're looking for opportunities to help with:

- **Dedupe** - Semantic deduplication ("IBM" = "International Business Machines")
- **Merge** - Join datasets without common keys (entity resolution)
- **Rank** - Sort by qualitative criteria requiring judgment
- **Screen** - Filter/categorize by natural language conditions
- **Enrich** - Add columns via web research

## Phase 1: Scan

Run the Python scanner for each subreddit:

```bash
python -m lib.scanner dataengineering
python -m lib.scanner excel
python -m lib.scanner salesforce
```

Each call outputs JSON to stdout with recent posts from that subreddit. Collect all results into a single list. If a subreddit fails (rate limited, unavailable), log the failure and continue with the others.

### Deduplication

Deduplicate against `data/seen.txt` - skip any URL that already appears in that file. Append new URLs to `data/seen.txt`. Create the file if it doesn't exist.

After deduplication, if no new posts remain, skip to Phase 4 (Report) with an empty report.

### Initial Filtering

For each post, do a quick first-pass judgment: is this even potentially about a data problem? Skip posts that are clearly:

- Job postings or career questions
- Product announcements or release notes
- Memes, jokes, or off-topic discussion
- Posts with no text body (link-only)

Log skipped posts and why. Keep everything else for classification.

## Phase 2: Classify

For each remaining post, answer ALL of these questions. Be concise but specific. Use your judgment for implicit signals even without explicit statements.

### Product Fit

1. **canonical**: Is this a common problem others face daily, or bespoke/niche? A canonical problem means a response helps thousands of future readers, not just one person.
2. **best_product**: Which of our products is most relevant? (Dedupe, Merge, Rank, Screen, Enrich)
3. **data_format**: What format is the data? (database, CSV, spreadsheet, CRM, API, etc.)
4. **row_count**: How many rows? Quote if stated, "not specified" if unknown.

### Technical Context

5. **tools_tried**: What tools have they already tried? If they've tried fuzzy matching and it failed, they understand why their problem is hard.
6. **tried_llms**: Have they tried using LLMs for this? Have they tried ChatGPT or similar? A third of people now try LLMs before asking for help.

### Data Characteristics

7. **difficulty**: How hard is the task? (e.g., "minor name variations" vs "multilingual entity matching" vs "rank on subjective quality signals")
8. **data_provided**: Is sample data provided in the post? Sample data makes demo matching much easier.
9. **accuracy_expectation**: What accuracy level do they expect or imply?

### Commercial Signals

10. **importance**: Does this look important? Business process blocked? Evidence of willingness to pay? "Our admin is drowning" is a different signal than "just curious."
11. **person_importance**: Does the person look important? Do they identify themselves? Technical skills? A StackOverflow user with high reputation answering "there's no solution" makes the thread more visible.
12. **commenter_solutions**: What are commenters saying? If someone already solved it with a native platform feature - and the poster accepted the answer - there's no opportunity.
13. **freshness**: Is this recent enough to engage with? Old threads can still be valuable if the question was never properly answered.

### Scoring

Based on your answers, assign a score from 1 to 5. The main question: "Would a comment describing an LLM-based approach be useful for people reading this post?"

| Score | Meaning |
|-------|---------|
| **1** | Not a fit - not a data problem, or trivially solvable with existing tools |
| **2** | Weak fit - data problem but exact matching / VLOOKUP / simple SQL would work |
| **3** | Possible fit - could benefit from semantic understanding, but might be too niche or platform-specific |
| **4** | Good fit - clear need for semantic matching or AI-powered processing, readers would benefit from knowing LLM approaches exist |
| **5** | Excellent fit - perfect use case, high visibility, a helpful response would get upvoted |

**Important:** At no point should you write a Python script for classification. Read the posts and think about them. If you feel like you need to write code, you've misunderstood these instructions.

Write all classifications to `data/classified/scan-<date>.json`:

```json
{
  "classified_at": "ISO timestamp",
  "classifications": [
    {
      "url": "...",
      "title": "...",
      "subreddit": "...",
      "answers": {
        "canonical": "...",
        "best_product": "...",
        "data_format": "...",
        "row_count": "...",
        "tools_tried": "...",
        "tried_llms": "...",
        "difficulty": "...",
        "data_provided": "...",
        "accuracy_expectation": "...",
        "importance": "...",
        "person_importance": "...",
        "commenter_solutions": "...",
        "freshness": "..."
      },
      "score": 4,
      "summary": "One-line explanation of why this score"
    }
  ],
  "metrics": {
    "total_classified": 25,
    "score_distribution": {"1": 15, "2": 5, "3": 3, "4": 1, "5": 1}
  }
}
```

Most posts will score 1-2. That's expected. A 2-3% hit rate is normal.

## Phase 3: Propose

For opportunities scoring 4 or 5, generate a response proposal.

### Strategy Selection

Choose a strategy based on the audience and context:

| Strategy | Use When |
|----------|----------|
| `PROVE_CAPABILITY` | Default (~80%). Show a demo or example proving we solve the problem. |
| `SHOW_SDK_CODE` | Technical audience (StackOverflow, GitHub). Lead with a code snippet. |
| `EXPLAIN_APPROACH` | Audience wants to understand *why* LLMs beat fuzzy matching. |
| `SHOW_INTEGRATION` | User is building workflows (Make, Zapier, n8n). Show how results fit their pipeline. |
| `OFFER_HANDS_ON` | Recent post, engaged OP. Offer to run their actual data. |

### Draft Response

Write a draft forum reply for each opportunity. The draft should:

1. **Acknowledge the problem** - Show you understand what they're dealing with
2. **Explain why existing approaches fall short** - Reference what they or commenters have tried
3. **Show the LLM-based approach** - Code snippet, demo reference, or explanation
4. **Be helpful on its own merits** - If someone stripped the product mention, would this answer still be useful?

The draft is an anchor for the human reviewer, not the final post. Keep the tone helpful, not salesy.

### Output

Write proposals to `data/proposals/scan-<date>.json`:

```json
{
  "proposed_at": "ISO timestamp",
  "proposals": [
    {
      "url": "...",
      "title": "...",
      "score": 5,
      "product": "Dedupe",
      "strategy": "SHOW_SDK_CODE",
      "reasoning": "Why this strategy for this opportunity",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "draft": "The actual forum response text..."
    }
  ]
}
```

If no opportunities scored 4-5, skip this phase.

## Phase 4: Report

Write a markdown report to `data/reports/scan-<date>.md`:

```markdown
# Community Scan Report - <date>

## Summary

| Metric | Count |
|--------|-------|
| Subreddits scanned | N |
| Posts fetched | N |
| After dedup | N |
| After initial filter | N |
| Classified | N |
| Score 4-5 | N |
| Score 3 | N |
| Score 1-2 | N |
| Proposals generated | N |

## Score Distribution

| Score | Count | % |
|-------|-------|---|
| 5 | N | N% |
| 4 | N | N% |
| 3 | N | N% |
| 2 | N | N% |
| 1 | N | N% |

## Top Opportunities (Score 4-5)

### [Score X] <title> (<subreddit>)
- **URL:** <url>
- **Product:** <best_product>
- **Strategy:** <strategy>
- **Summary:** <classifier summary>

**Key Points:**
- <key points from proposal>

<details>
<summary>Draft Response (click to expand)</summary>

<draft response text>

</details>

## All Classifications

| Score | Subreddit | Title | URL |
|-------|-----------|-------|-----|
| ... | ... | ... | ... |

## Skipped Posts

| Reason | Count |
|--------|-------|
| Already in seen.txt | N |
| No text body | N |
| Career/job posting | N |
| Product announcement | N |
```

If no posts were found or all scored 1-2, the report should still be created noting that. An empty run is still a data point.

## Phase 5: Git & PR

1. Create a branch named `scan/<date>`
2. Add and commit:
   - `data/reports/scan-<date>.md`
   - `data/classified/scan-<date>.json`
   - `data/proposals/scan-<date>.json` (if it exists)
   - `data/seen.txt`
3. Push and create a PR titled "Community scan: <date>"

The PR is the output. A human opens it, reads the report, expands the draft responses, tweaks the wording, and decides what to post. GitHub is the UI.

## Learnings

After each run, check if any process improvements were discovered and update `data/learnings.md`. These aren't logs - they're instructions for future runs. Examples:

```
- "r/excel: most posts are formula syntax questions, not data problems. Consider removing."
- "Posts starting with 'What's your favorite...' are never opportunities. Skip during initial filter."
- "Competitor marketing posts account for ~50% of Reddit noise. Look for: product links in post body, account history of only posting about one tool."
- "r/dataengineering: 3% hit rate. Keep scanning."
```

Before scanning, read `data/learnings.md` if it exists and apply any relevant instructions (e.g., skip certain subreddits, adjust filtering).

The learnings file is the pipeline's memory. Over time it accumulates knowledge about which sources work, what patterns to ignore, and what signals matter. This is one of the most valuable outputs of the whole system.

## Error Recovery

- **Subreddit fetch fails:** Log failure, continue with others
- **Classification fails for a post:** Log it, continue with remaining posts
- **Proposal generation fails:** Log it, still produce the report
- **Git/PR fails:** Report the error, don't lose the report file

Never fail the entire skill due to individual component failures. Always produce a report.
