# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anton is an AI-powered autonomous code fixing pipeline. It receives webhooks from JIRA, Datadog, and SonarCloud, routes them through an LLM orchestrator, and dispatches ephemeral Kubernetes Jobs that fix code and open pull requests.

## Architecture

Three decoupled Python 3.11 microservices communicate via RabbitMQ:

```
Webhooks → Ingester (FastAPI) → RabbitMQ → Orchestrator → K8s Job (Runner) → GitHub PR
```

- **Ingester** (`ingester/`) — FastAPI webhook receiver. Validates HMAC signatures, normalizes payloads into `AgentTask` schema, publishes to RabbitMQ (`agent_events` exchange, `task.created` routing key).
- **Orchestrator** (`orchestrator/`) — RabbitMQ consumer. Uses Claude to route tasks (template selection, complexity, required skills), then creates a K8s ConfigMap + Job from Jinja2 templates (`orchestrator/templates/base_job.yaml.j2`).
- **Runner** (`runner/`) — Ephemeral K8s Job. Clones repo, runs a Coder loop (Claude, max 15 turns with tools) → Reviewer loop (GPT-4o, max 3 rejections) → commits and opens PR via `gh` CLI.

## Build & Run Commands

```bash
# Build Docker images
docker build -t agent-ingester:latest ingester/
docker build -t agent-runner:latest runner/

# Run ingester locally with RabbitMQ
cd ingester && docker compose up

# Run runner locally (requires env vars)
cd runner && python -m app

# Install dependencies per service
pip install -r ingester/requirements.txt
pip install -r orchestrator/requirements.txt
pip install -r runner/requirements.txt
```

There are currently no test suites, linting, or formatting commands configured.

## Key Patterns

- **Pydantic Settings** for config in each service (`app/config.py`)
- **Structured JSON logging** via python-json-logger (`app/logging_config.py` in each service), with `task_id` traced end-to-end
- **Normalizer registry** pattern in ingester (`app/normalizers/registry.py`) — factory maps source to normalizer class
- **HMAC webhook verification** via FastAPI dependency injection (`ingester/app/api/dependencies.py`)
- **Async RabbitMQ** via aio-pika — topic exchange with DLQ retry logic in orchestrator
- **Runner tools**: `read_file`, `write_file`, `run_shell_command`, `list_dir`, `git_status`, `submit_changes` — with path traversal protection

## Key Environment Variables

| Variable | Used By | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | orchestrator, runner | — |
| `OPENAI_API_KEY` | runner | — |
| `GITHUB_TOKEN` | runner | — |
| `RABBITMQ_URL` | ingester, orchestrator | `amqp://rabbit:rabbit@rabbitmq:5672/` |
| `WEBHOOK_SECRET` | ingester | `changeme-in-production` |
| `K8S_NAMESPACE` | orchestrator | `agents` |
| `AGENT_IMAGE` | orchestrator | `agent-runner:latest` |

## Important File Locations

- Entry points: `ingester/app/main.py`, `orchestrator/app/main.py`, `runner/app/__main__.py`
- Data models: `*/app/models.py` (or `*/app/models/`)
- K8s Job template: `orchestrator/templates/base_job.yaml.j2`
- Runner tools & coder loop: `runner/app/agent_tools.py`, `runner/app/runner.py`
- Reviewer (GPT-4o): `runner/app/reviewer.py`
