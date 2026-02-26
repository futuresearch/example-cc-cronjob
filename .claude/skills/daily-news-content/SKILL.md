---
name: daily-news-content
description: Generate news-driven data content using the everyrow SDK. Orchestrates news discovery, dataset finding, SDK execution, and graphics generation. Use when asked to "run the news pipeline", "generate daily content", or "find news content".
---

# Daily News Content Pipeline

Orchestrates the complete pipeline: news -> datasets -> SDK -> graphics -> report.

**Goal:** Find today's news stories with data angles, construct datasets, run everyrow rank/screen demos on them, and prepare visualizations for human review.

This is a simplified version of a production pipeline that generates marketing content daily. It demonstrates multi-agent orchestration: a coordinator skill dispatches work to four specialized agents (news-finder, dataset-finder, sdk-runner, graphics-generator), each running as a subagent with its own tools and instructions.

## How It Works

```
Phase 1: Find News
  └── news-finder agent scans RSS feeds for stories with data angles
       ↓ 10 candidates with headlines, URLs, and data angle descriptions
Phase 2: Discover Datasets
  └── dataset-finder agents find relevant datasets (Wikipedia tables, government data)
       ↓ CSV files with entities for each viable candidate
Phase 3: Run SDK
  └── sdk-runner agents call everyrow rank/screen on the datasets
       ↓ ranked/screened results with evaluation scores
Phase 4: Generate Graphics
  └── graphics-generator agents create SVG visualizations
       ↓ two SVG variations per post-worthy result
Phase 5: Report + PR
  └── markdown report, branch, commit, push, PR
```

The output is a pull request containing a report, SDK results, and graphics. A human opens it, picks the best graphic variations, and publishes.

## Editorial Criteria

The pipeline prioritizes content that is **entertaining and surprising**, not just informative.

**Prioritize stories that are both absurd AND major conventional news.** The best stories make people say "wait, really?" - they involve powerful entities doing ridiculous things, situations with inherent irony, massive scale surprises, or norms being violated by people who should know better.

**Each agent contributes to the humor:**

- **news-finder**: Selects stories that are absurd and newsworthy
- **dataset-finder**: Finds reference classes that enable surprising comparisons
- **sdk-runner**: Frames queries to surface the most absurd findings
- **graphics-generator**: Creates sardonic visualizations with editorial commentary

## Requirements

- `ANTHROPIC_API_KEY` - for Claude Code
- `EVERYROW_API_KEY` - for the everyrow SDK (get one at https://everyrow.io)
- `GH_TOKEN` - for creating pull requests
- `SSH_PRIVATE_KEY` - for git push

## Before Running

1. Note the current time (for runtime tracking)
2. Get today's date: `date +%Y-%m-%d`
3. Create output directory: `mkdir -p data/news-content/{date}`

## Phase 1: News Discovery

Spawn the news-finder agent to find today's top news stories with data angles.

```
Task (subagent_type: news-finder, max_turns: 30):
  "Find news opportunities for today. Date: {date}. Output to data/news-content/{date}/candidates.json"
```

The agent scans RSS feeds (BBC Business, TechCrunch, Hacker News, and others) and selects the top 10 stories that have a "data angle" - a set of entities that can be ranked or screened using the everyrow SDK.

### Expected Output

- `data/news-content/{date}/candidates.json` - Top 10 candidates

Each candidate includes:

```json
{
  "headline": "Say goodbye to free ChatGPT with no ads",
  "url": "https://www.axios.com/2026/02/09/chatgpt-ads-testing",
  "source": "techcrunch_ai",
  "published_at": "2026-02-09T14:00:00Z",
  "description": "OpenAI begins testing ads in ChatGPT free tier...",
  "data_angle": {
    "product": "rank",
    "entities": "AI chatbots/assistants",
    "criteria": "How long each chatbot remained ad-free from launch",
    "dataset_description": "List of major AI chatbots with launch dates",
    "viability": 5,
    "reasoning": "Clear reference class, enables surprising comparisons"
  }
}
```

### Verify Output

```bash
cat data/news-content/{date}/candidates.json | python3 -m json.tool | head -30
```

Check that the file exists, is valid JSON, and has 10 candidates each with a `data_angle`.

If news-finder fails, stop the pipeline and write a minimal report explaining the failure.

## Phase 2: Dataset Discovery

For each candidate with `viability >= 3`, spawn dataset-finder agents in parallel.

### Filter Candidates

Read `candidates.json` and filter to viable ones:

```python
viable = [c for c in candidates if c["data_angle"]["viability"] >= 3]
```

### Run Dataset Finders (Batches of 3)

```
Task (subagent_type: dataset-finder, max_turns: 20):
  "Find dataset for candidate 0 in data/news-content/{date}"
Task (subagent_type: dataset-finder, max_turns: 20):
  "Find dataset for candidate 1 in data/news-content/{date}"
Task (subagent_type: dataset-finder, max_turns: 20):
  "Find dataset for candidate 2 in data/news-content/{date}"
```

Wait for each batch, then launch the next. Continue until all viable candidates are processed.

### Expected Output

For each candidate:

- `data/news-content/{date}/datasets/candidate-{index}.json` - metadata (source URL, entity type, row count)
- `data/news-content/{date}/datasets/candidate-{index}/dataset.csv` - the actual CSV

### Handling Failures

If a dataset-finder fails or times out:

- Log the failure
- Mark status as "failed" in tracking
- Continue with other candidates
- Do NOT retry

## Phase 3: SDK Execution

For each candidate with a found dataset, run sdk-runner agents in parallel batches of 5.

```
Task (subagent_type: sdk-runner, max_turns: 25):
  "Run SDK for candidate 0 in data/news-content/{date}"
```

The sdk-runner decides whether to use rank or screen, crafts a task prompt, writes and executes a Python script that calls the everyrow SDK, and evaluates the results.

### Expected Output

- `data/news-content/{date}/sdk-results/candidate-{index}.json` - evaluation and metadata
- `data/news-content/{date}/sdk-results/candidate-{index}.csv` - raw SDK output

Each result includes a self-evaluation:

```json
{
  "evaluation": {
    "discrimination": 5,
    "surprise": 5,
    "clarity": 5,
    "timeliness": 5,
    "overall": 5,
    "post_worthy": true,
    "key_findings": [
      "Microsoft Copilot lasted only 9 days ad-free",
      "Siri has been ad-free for 5,242 days (14+ years)"
    ],
    "suggested_headline": "How Long Can an AI Chatbot Resist Ads?"
  }
}
```

**Self-evaluation criteria:**

| Criterion | What It Measures |
|-----------|-----------------|
| **Discrimination** | Meaningful spread in scores? (30-95 good, all 70-80 bad) |
| **Surprise** | Unexpected results that make people say "wait, really?" |
| **Clarity** | Easy to explain in a tweet or headline? |
| **Timeliness** | Connects meaningfully to today's news story? |

### Handling Failures

- If sdk-runner fails, log it and continue with others
- If results are boring (low discrimination, no surprise), mark as not post-worthy

## Phase 4: Graphics Generation

For each candidate with `post_worthy: true`, spawn graphics-generator agents.

```
Task (subagent_type: graphics-generator, max_turns: 30):
  "Generate graphics for data/news-content/{date}/sdk-results/candidate-0.json"
```

The graphics-generator creates **two meaningfully different SVG variations** for each result. A human reviewer picks the better one.

### Expected Output

- `data/news-content/{date}/graphics/{slug}-v1.svg`
- `data/news-content/{date}/graphics/{slug}-v2.svg`

If no post-worthy results exist, skip this phase.

### Convert SVGs to PNGs

After all graphics are generated:

```bash
for svg in data/news-content/{date}/graphics/*.svg; do
    rsvg-convert -w 1200 "$svg" -o "${svg%.svg}.png"
done
```

## Phase 5: Report + PR

Write a markdown report to `data/news-content/{date}/report.md` summarizing the pipeline run:

```markdown
# Daily News Content Report - {date}

## Summary

| Stage           | Input           | Output      | Success   |
|-----------------|-----------------|-------------|-----------|
| News Discovery  | ~150 headlines  | 10 candidates | ok      |
| Dataset Finding | {N} viable      | {N} found   | {N}/{M}   |
| SDK Execution   | {N} with data   | {N} run     | {N}/{M}   |
| Graphics        | {N} post-worthy | {N} pairs   | {N}/{M}   |

**Post-worthy results: {N}**

## Post-Worthy Results

### 1. {headline}

**News:** [{headline}]({url})
**Operation:** rank
**Session:** {everyrow session URL}

**Key Findings:**
- {finding 1}
- {finding 2}

**Graphics:** `graphics/{slug}-v1.svg`, `graphics/{slug}-v2.svg`

## Not Post-Worthy

| # | Headline | Operation | Reason |
|---|----------|-----------|--------|

## Skipped or Failed

| # | Headline | Stage | Reason |
|---|----------|-------|--------|
```

### Create Branch and PR

```bash
BRANCH="news-content/{date}"
git checkout -b "$BRANCH"
git add data/news-content/{date}/
git commit -m "Daily news content: {date}"
git push origin "$BRANCH"
gh pr create \
  --title "Daily news content: {date}" \
  --body "$(cat data/news-content/{date}/report.md)"
```

## File Structure

```
data/news-content/{date}/
  candidates.json              # news-finder output (10 candidates)
  datasets/
    candidate-0.json           # dataset metadata
    candidate-0/
      dataset.csv              # the actual CSV (max 1000 rows)
  sdk-results/
    candidate-0.json           # evaluation + session URL
    candidate-0.csv            # raw SDK output
  graphics/
    {slug}-v1.svg              # graphic variation 1
    {slug}-v1.png              # PNG export (1200px wide)
    {slug}-v2.svg              # graphic variation 2
    {slug}-v2.png              # PNG export
  report.md                    # pipeline summary
```

## Error Recovery

- **news-finder fails:** Stop pipeline, write minimal report
- **dataset-finder fails for one candidate:** Continue with others
- **sdk-runner fails for one candidate:** Continue with others
- **graphics-generator fails:** Candidate still post-worthy, note missing graphics
- **All datasets fail:** Write report showing all failures
- **All SDK runs fail:** Write report, suggest checking EVERYROW_API_KEY

Never fail silently. Always produce a report explaining what happened.

## Customization

- **RSS feeds to scan:** Edit `.claude/agents/news-finder.md` to change the feed list
- **Evaluation criteria:** Adjust the self-evaluation rubric in `.claude/agents/sdk-runner.md`
- **Visualization styles:** Add styles to the menu in `.claude/agents/graphics-generator.md`
- **Data sources:** Extend the routing table in `.claude/agents/dataset-finder.md`
