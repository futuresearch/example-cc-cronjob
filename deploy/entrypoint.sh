#!/bin/bash
set -e

# Required env vars:
#   SKILL_NAME       - which skill to run (e.g., "add-numbers")
#   ANTHROPIC_API_KEY - Claude API key
#   SSH_PRIVATE_KEY   - for git push (deploy key or user key)
#   GH_TOKEN          - for gh CLI (creating PRs)
#
# Optional env vars:
#   SKILL_PROMPT     - custom prompt (default: "please read and execute {SKILL_NAME} skill")

SKILL_NAME="${SKILL_NAME:?SKILL_NAME env var is required}"
SKILL_PROMPT="${SKILL_PROMPT:-please read and execute ${SKILL_NAME} skill}"

echo "=== Claude Code CronJob: ${SKILL_NAME} ==="
echo "Date: $(date)"
echo "Prompt: ${SKILL_PROMPT}"

# ── Set up git + GitHub CLI ──────────────────────────────────────
git config --global user.email "claudie-bot@example.com"
git config --global user.name "Claudie Bot"

mkdir -p ~/.ssh
echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_ed25519
chmod 600 ~/.ssh/id_ed25519
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

cd ~/app

# ── Run Claude Code ──────────────────────────────────────────────
# Save raw JSONL for debugging, pipe filtered output to stdout
RAW_LOG="/tmp/claude-raw-${SKILL_NAME}-$(date +%s).jsonl"
CLAUDE_EXIT=0

export SKILL_PROMPT RAW_LOG
timeout 3600 bash -c 'claude -p \
    --dangerously-skip-permissions \
    --verbose \
    --output-format stream-json \
    -- "$SKILL_PROMPT"' \
    | tee "$RAW_LOG" \
    | jq --unbuffered -r '
if .type == "assistant" then
  .message.content[]? |
  if .type == "text" then ">>> " + .text[0:5000]
  elif .type == "tool_use" then "[" + .name + "] " + ((.input | tostring)[0:3000])
  else empty end
elif .type == "result" then
  "[done] " + (.result // "complete")[0:5000]
else empty end' || CLAUDE_EXIT=$?

# ── Safety net: if Claude timed out, salvage partial results ─────
if [ "$CLAUDE_EXIT" -eq 124 ]; then
    echo "=== TIMEOUT: Claude exceeded time limit ==="
    echo "Running cleanup..."
    timeout 300 claude -p --dangerously-skip-permissions -- \
        "The previous Claude process timed out. Check what partial results exist and write a summary to /tmp/partial-report.md."
fi

echo "=== Pipeline complete: ${SKILL_NAME} (exit: ${CLAUDE_EXIT}) ==="
