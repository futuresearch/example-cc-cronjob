# Claude Code as a Kubernetes CronJob — Minimal Example

A minimal, runnable example of running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as a Kubernetes CronJob.

This repo accompanies the blog series: **Running Claude Code as a Production Runtime**.

## What's Here

Four example skills that share the same Dockerfile, entrypoint, and Helm chart:

### 1. `add-numbers` — Hello World

A trivial skill that computes 2 + 3, writes the result to a file, and creates a PR. Demonstrates the basic pattern: Python does mechanics, Claude does orchestration.

### 2. `community-scanner` — Real-World Example

A simplified version of the community scanning pipeline from [Post 3](https://everyrow.io/blog/marketing-pipeline-using-claude-code). Scans a few subreddits for people with data problems, classifies opportunities with a 5-question rubric, and creates a PR with a report.

This demonstrates the production pattern at small scale: Python fetches posts, Claude reads them and decides which ones matter.

### 3. `seo-pipeline` — SEO Optimization

A simplified version of the SEO optimization pipeline from [Post 4](https://everyrow.io/blog/llm-agents-seo-pipeline). Collects Google Search Console data via MCP, analyzes every page with an LLM agent, and proposes title/description improvements as a PR.

This demonstrates the feedback loop pattern: each run measures the outcome of previous experiments (did that title change improve CTR?), and the analyzer uses that history to make better suggestions over time.

### 4. `daily-news-content` — Multi-Agent Content Pipeline

A simplified version of the news content pipeline from [Post 5](https://everyrow.io/blog/dogfooding-your-sdk-with-claude-code). Scans RSS feeds for news stories with data angles, finds datasets, runs the everyrow SDK to rank/screen entities, generates SVG graphics, and creates a PR with results.

This demonstrates multi-agent orchestration: a coordinator skill dispatches work to four specialized agents (news-finder, dataset-finder, sdk-runner, graphics-generator), each with its own tools and instructions. It also demonstrates "dogfooding" - using your own product's SDK inside your automation pipeline.

```
.claude/
  skills/
    add-numbers/SKILL.md          # Trivial example: compute and PR
    community-scanner/SKILL.md    # Scan → Classify → Propose → Report → PR
    seo-pipeline/SKILL.md         # Collect GSC → Analyze → Propose → Report → PR
    daily-news-content/SKILL.md   # News → Datasets → SDK → Graphics → PR
  agents/
    classifier.md                 # 13-question rubric, 1-5 scoring
    proposer.md                   # Strategy selection, draft forum responses
    seo-page-analyzer.md          # Per-page SEO analysis with experiment tracking
    news-finder.md                # RSS scanning, data angle identification
    dataset-finder.md             # Wikipedia/public data sourcing
    sdk-runner.md                 # everyrow rank/screen execution
    graphics-generator.md         # SVG visualization with iterative refinement
lib/
  add_numbers.py                  # Python utility for add-numbers
  scanner.py                      # Reddit JSON API fetcher (with optional comment enrichment)
  seo_prepare.py                  # GSC data processor: raw JSON → per-page input files
  news_feeds.py                   # RSS feed fetcher (stdlib only, no API keys)
Dockerfile                        # Multi-stage build with Python + Node + Claude CLI
deploy/
  entrypoint.sh                   # Runs Claude Code with jq log filtering + timeout safety net
  cronjob.yaml                    # Standalone K8s CronJob manifest
  chart/                          # Helm chart (for managing multiple skills)
    Chart.yaml
    values.yaml
    templates/cronjob.yaml
pyproject.toml                    # Python project (add your dependencies here)
```

## Quick Start

### 1. Build the image

```bash
docker build -t claudie:latest .
```

### 2. Test locally

**Add numbers (hello world):**

```bash
docker run \
  -e ANTHROPIC_API_KEY="sk-..." \
  -e SKILL_NAME="add-numbers" \
  -e SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" \
  -e GH_TOKEN="ghp_..." \
  claudie:latest
```

**Community scanner:**

```bash
docker run \
  -e ANTHROPIC_API_KEY="sk-..." \
  -e SKILL_NAME="community-scanner" \
  -e SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" \
  -e GH_TOKEN="ghp_..." \
  claudie:latest
```

**SEO pipeline:**

```bash
# Requires Google Search Console API credentials.
# See: https://github.com/AminForou/mcp-gsc for setup.
docker run \
  -e ANTHROPIC_API_KEY="sk-..." \
  -e SKILL_NAME="seo-pipeline" \
  -e SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" \
  -e GH_TOKEN="ghp_..." \
  -v /path/to/gsc-credentials.json:/gsc-credentials.json \
  -e GSC_CREDENTIALS_PATH="/gsc-credentials.json" \
  claudie:latest
```

**Daily news content:**

```bash
# Requires an everyrow API key for the SDK.
# Get one at: https://everyrow.io
docker run \
  -e ANTHROPIC_API_KEY="sk-..." \
  -e SKILL_NAME="daily-news-content" \
  -e SSH_PRIVATE_KEY="$(cat ~/.ssh/id_ed25519)" \
  -e GH_TOKEN="ghp_..." \
  -e EVERYROW_API_KEY="ek_..." \
  claudie:latest
```

### 3. Deploy to Kubernetes

**Option A: Plain CronJob**

```bash
# Create the secret (API key, SSH deploy key, GitHub token)
kubectl create secret generic claudie-secrets \
  --from-literal=ANTHROPIC_API_KEY="sk-..." \
  --from-literal=SSH_PRIVATE_KEY="$(cat ~/.ssh/deploy_key)" \
  --from-literal=GH_TOKEN="ghp_..."

# Apply the CronJob
kubectl apply -f deploy/cronjob.yaml
```

**Option B: Helm chart** (useful when you have multiple skills)

```bash
# Edit deploy/chart/values.yaml to set your image registry
helm install claudie deploy/chart/
```

### 4. Add your own skill

Create `.claude/skills/my-skill/SKILL.md` with a markdown description of what the skill should do, then either:

- Update `deploy/cronjob.yaml` to set `SKILL_NAME: "my-skill"`, or
- Add a new entry to `deploy/chart/values.yaml`:

```yaml
jobs:
  - name: my-skill
    skillName: my-skill
    schedule: "0 9 * * 1-5"
```

## Customizing the Community Scanner

Edit `.claude/skills/community-scanner/SKILL.md` to change:

- **Which subreddits to scan** — replace the list in the Configuration section
- **Classification criteria** — adjust the questions in Phase 2 to match what you're looking for
- **Report format** — modify Phase 3 to include whatever you need

The `lib/scanner.py` fetches posts using Reddit's public JSON API (no authentication needed). For other platforms, you'd add similar fetchers - the pattern is the same: Python handles the API mechanics, Claude handles the judgment.

## Customizing the SEO Pipeline

Edit `.claude/skills/seo-pipeline/SKILL.md` to change:

- **Which domain to track** — replace `sc-domain:example.com` with your GSC property
- **Batch size** — adjust the number of parallel agents in Phase 3 (default: 5)
- **Report format** — modify the Phase 5 template to match what you want in the PR

Edit `.claude/agents/seo-page-analyzer.md` to change:

- **Decision framework** — which page categories get aggressive experiments vs. conservative suggestions
- **Title format preferences** — which title formats to try and how to rotate them
- **Confidence thresholds** — when to suggest changes vs. recommend waiting

Edit `lib/seo_prepare.py` to change:

- **`DOMAIN`** — your site's domain (must match GSC URLs)
- **`CONTENT_DIR`** — where your markdown/MDX content files live
- **`PAGE_CATEGORIES`** — map slugs to categories (blog, docs, landing) for the analyzer

The pipeline uses an MCP server ([mcp-server-gsc](https://github.com/AminForou/mcp-gsc)) to fetch Search Console data. You'll need a Google Cloud service account with Search Console API access.

## Customizing the Daily News Content Pipeline

Edit `.claude/skills/daily-news-content/SKILL.md` to change:

- **Pipeline phases** — skip graphics generation, adjust batch sizes, change timeout policies
- **Editorial criteria** — what makes a story worth pursuing (currently: absurd + newsworthy)
- **Report format** — modify the Phase 5 template

Edit `.claude/agents/news-finder.md` to change:

- **RSS feeds to scan** — add/remove feeds from the source list (all must be public, no API keys)
- **Selection criteria** — what makes a good "data angle" (entity types, viability scoring)

Edit `.claude/agents/dataset-finder.md` to change:

- **Data sources** — extend the routing table with new sources beyond Wikipedia
- **Entity types** — add new entity type -> source mappings

Edit `.claude/agents/sdk-runner.md` to change:

- **Evaluation criteria** — adjust discrimination/surprise/clarity/timeliness scoring
- **Row limits** — change 10 (rank) / 50 (screen) defaults
- **Post-worthy threshold** — what overall score counts as publishable

Edit `.claude/agents/graphics-generator.md` to change:

- **Visualization styles** — add new styles to the menu or change which is the default
- **Color palette** — replace the indigo brand colors with your own
- **Refinement budget** — increase/decrease the 5-attempt limit

The `lib/news_feeds.py` fetches RSS feeds using only Python stdlib (no API keys needed). To add feeds, edit the `FEEDS` dictionary at the top of the file.

**Note:** The SDK execution phase requires an `EVERYROW_API_KEY`. Get one at https://everyrow.io. See the SDK docs for [rank](https://everyrow.io/docs/reference/RANK) and [screen](https://everyrow.io/docs/reference/SCREEN).

## Key Details

- **Claude CLI needs Node.js** — hence the `python-nodejs` base image
- **`hasCompletedOnboarding`** — without this in `~/.claude.json`, Claude hangs waiting for interactive setup
- **`--dangerously-skip-permissions`** — lets Claude run commands without confirmation. Only use in ephemeral containers where the blast radius is acceptable
- **`--output-format stream-json`** — gives you JSONL output; the entrypoint pipes it through `jq` for readable logs
- **Timeout safety net** — if Claude hangs, `timeout` kills it and a second Claude instance salvages partial results
