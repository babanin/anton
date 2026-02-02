# anton

AI-powered autonomous code fixing pipeline. Receives events from external systems, routes them through an LLM-based orchestrator, and dispatches agent jobs that fix code and open pull requests.

## Architecture

```
Webhooks (JIRA, Datadog, SonarCloud)
        │
        ▼
   ┌──────────┐     ┌──────────────┐     ┌────────────┐
   │ Ingester  │────▶│ Orchestrator │────▶│   Runner   │
   │ (FastAPI) │     │  (Consumer)  │     │  (K8s Job) │
   └──────────┘     └──────────────┘     └────────────┘
        │ RabbitMQ       │ K8s API            │ GitHub
        ▼                ▼                    ▼
   Normalized       Route + dispatch      Clone, fix,
   AgentTask        as K8s Jobs           review, PR
```

- **Ingester** — FastAPI service that receives webhooks from JIRA, Datadog, and SonarCloud. Normalizes events into a unified `AgentTask` schema and publishes to RabbitMQ.
- **Orchestrator** — Consumes tasks from RabbitMQ, uses Claude to route and assess complexity, then dispatches Kubernetes Jobs with the appropriate configuration.
- **Runner** — Docker image executed as a K8s Job. Clones the target repo, runs a Coder (Claude) + Reviewer (GPT-4o) loop, and opens a pull request with the fix.

## Directory Structure

```
ingester/       Webhook receiver and normalizer
orchestrator/   Task router and K8s job dispatcher
runner/         Autonomous code fixing agent
```

## Prerequisites

- Python 3.11+
- Docker
- Kubernetes cluster (for production deployment)
- RabbitMQ instance

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | orchestrator, runner |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o reviewer | runner |
| `GITHUB_TOKEN` | GitHub token for cloning and PR creation | runner |
| `RABBITMQ_URL` | RabbitMQ connection string | ingester, orchestrator |
| `WEBHOOK_SECRET` | Secret for validating incoming webhooks | ingester |

## Quick Start

```bash
# Build images
docker build -t agent-ingester:latest ingester/
docker build -t agent-runner:latest runner/

# Run ingester locally with RabbitMQ
cd ingester && docker compose up

# Run runner locally (requires task.json and env vars)
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export GITHUB_TOKEN=...
python -m app  # from runner/
```

## Kubernetes Deployment

Secrets are expected in a K8s Secret named `agent-secrets`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-secrets
stringData:
  anthropic-api-key: <your-key>
  openai-api-key: <your-key>
  github-token: <your-token>
```

The orchestrator creates Jobs from `orchestrator/templates/base_job.yaml.j2`, mounting task configuration as a ConfigMap at `/app/context/task.json`.
