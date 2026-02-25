# Claude Code as a Kubernetes CronJob — Minimal Example

A minimal, runnable example of running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as a Kubernetes CronJob.

This repo accompanies the blog series: **Running Claude Code as a Production Runtime**.

## What's Here

```
.claude/skills/add-numbers/SKILL.md   # Example skill: computes 2 + 3, commits result, creates PR
lib/add_numbers.py                     # Python utility called by the skill
Dockerfile                             # Multi-stage build with Python + Node + Claude CLI
deploy/
  entrypoint.sh                        # Runs Claude Code with jq log filtering + timeout safety net
  cronjob.yaml                         # Standalone K8s CronJob manifest
  chart/                               # Helm chart (for managing multiple skills)
    Chart.yaml
    values.yaml
    templates/cronjob.yaml
pyproject.toml                         # Python project (add your dependencies here)
```

## Quick Start

### 1. Build the image

```bash
docker build -t claudie:latest .
```

### 2. Test locally

```bash
docker run \
  -e ANTHROPIC_API_KEY="sk-..." \
  -e SKILL_NAME="add-numbers" \
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

## Key Details

- **Claude CLI needs Node.js** — hence the `python-nodejs` base image
- **`hasCompletedOnboarding`** — without this in `~/.claude.json`, Claude hangs waiting for interactive setup
- **`--dangerously-skip-permissions`** — lets Claude run commands without confirmation. Only use in ephemeral containers where the blast radius is acceptable
- **`--output-format stream-json`** — gives you JSONL output; the entrypoint pipes it through `jq` for readable logs
- **Timeout safety net** — if Claude hangs, `timeout` kills it and a second Claude instance salvages partial results
