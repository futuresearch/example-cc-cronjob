# Build stage: install Python dependencies with uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-sources

# Runtime: Python + Node.js (Claude CLI needs Node)
FROM nikolaik/python-nodejs:python3.13-nodejs22

# jq for log filtering, gh for GitHub operations
RUN apt-get update \
    && apt-get install -y jq git-lfs gh \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash claudie
USER claudie
WORKDIR /home/claudie

# Install Claude CLI
RUN curl -fsSL https://claude.ai/install.sh | bash

# Skip interactive onboarding — without this, Claude hangs waiting for TTY input
RUN echo '{"hasCompletedOnboarding": true}' > /home/claudie/.claude.json

# Copy venv from build stage
USER root
COPY --from=build /app/.venv /home/claudie/.venv

# Copy project (skills, agents, lib, etc.)
COPY . /home/claudie/app
COPY deploy/entrypoint.sh /home/claudie/entrypoint.sh
RUN chmod +x /home/claudie/entrypoint.sh \
    && chown -R claudie:claudie /home/claudie

USER claudie
ENV PATH="/home/claudie/.venv/bin:/home/claudie/.local/bin:$PATH"
CMD ["/home/claudie/entrypoint.sh"]
