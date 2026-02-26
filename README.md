# Claude Code as a Kubernetes CronJob — Minimal Example

A minimal, runnable example of running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as a Kubernetes CronJob.

This repo accompanies the blog series: **Running Claude Code as a Production Runtime**.

## What's Here

Two example skills that share the same Dockerfile, entrypoint, and Helm chart:

### 1. `add-numbers` — Hello World

A trivial skill that computes 2 + 3, writes the result to a file, and creates a PR. Demonstrates the basic pattern: Python does mechanics, Claude does orchestration.

### 2. `community-scanner` — Real-World Example

A simplified version of the community scanning pipeline from [Post 3](https://everyrow.io/blog/marketing-pipeline-using-claude-code). Scans a few subreddits for people with data problems, classifies opportunities with a 5-question rubric, and creates a PR with a report.

This demonstrates the production pattern at small scale: Python fetches posts, Claude reads them and decides which ones matter.

```
.claude/
  skills/
    add-numbers/SKILL.md          # Trivial example: compute and PR
    community-scanner/SKILL.md    # Scan Reddit, classify, report, PR
  agents/
    classifier.md                 # Structured classification agent
lib/
  add_numbers.py                  # Python utility for add-numbers
  scanner.py                      # Reddit JSON API fetcher
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

## Key Details

- **Claude CLI needs Node.js** — hence the `python-nodejs` base image
- **`hasCompletedOnboarding`** — without this in `~/.claude.json`, Claude hangs waiting for interactive setup
- **`--dangerously-skip-permissions`** — lets Claude run commands without confirmation. Only use in ephemeral containers where the blast radius is acceptable
- **`--output-format stream-json`** — gives you JSONL output; the entrypoint pipes it through `jq` for readable logs
- **Timeout safety net** — if Claude hangs, `timeout` kills it and a second Claude instance salvages partial results
