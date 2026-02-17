# anton

![](anton.webp)
    
AI-powered autonomous code fixing pipeline. Receives events from external systems, routes them through an LLM-based orchestrator, and dispatches agent jobs that fix code and open pull requests.

## Architecture

```
Webhooks (JIRA, Datadog, SonarCloud)
        │
        ▼
   ┌──────────┐     ┌──────────────┐     ┌────────────┐
   │ Ingester │────▶│ Orchestrator │────▶│   Runner   │
   │ (FastAPI)│     │  (Consumer)  │     │  (K8s Job) │
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
charts/anton/          Helm chart for Kubernetes deployment
ingester/              Webhook receiver and normalizer
orchestrator/          Task router and K8s job dispatcher
runner/                Autonomous code fixing agent
.github/workflows/     CI/CD (Helm chart publishing)
```

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (dependency management)
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
docker build -t anton-ingester:latest ingester/
docker build -t anton-runner:latest runner/

# Run ingester locally with RabbitMQ
cd ingester && docker compose up

# Run runner locally (requires task.json and env vars)
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export GITHUB_TOKEN=...
uv run python -m app  # from runner/
```

## Kubernetes Deployment

Secrets are expected in a K8s Secret named `anton-secrets`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: anton-secrets
stringData:
  anthropic-api-key: <your-key>
  openai-api-key: <your-key>
  github-token: <your-token>
```

The orchestrator creates Jobs from `orchestrator/templates/base_job.yaml.j2`, mounting task configuration as a ConfigMap at `/app/context/task.json`.

## Helm Chart

A Helm chart is available for configurable Kubernetes deployments.

### Add the repo

```bash
helm repo add anton https://babanin.github.io/anton
helm repo update
```

### Install

```bash
helm install anton anton/anton \
  --namespace agents --create-namespace \
  --set secrets.anthropicApiKey="sk-..." \
  --set secrets.openaiApiKey="sk-..." \
  --set secrets.githubToken="ghp_..." \
  --set secrets.webhookSecret="your-webhook-secret"
```

### External RabbitMQ

```bash
helm install anton anton/anton \
  --namespace agents --create-namespace \
  --set rabbitmq.enabled=false \
  --set ingester.rabbitmqUrl="amqp://user:pass@rabbitmq.example.com:5672/" \
  --set orchestrator.rabbitmqUrl="amqp://user:pass@rabbitmq.example.com:5672/"
```

### Enable Ingress

```bash
helm install anton anton/anton \
  --namespace agents --create-namespace \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set "ingress.hosts[0].host=anton.example.com" \
  --set "ingress.hosts[0].paths[0].path=/"
```

### Uninstall

```bash
helm uninstall anton -n agents
```

See [`charts/anton/values.yaml`](charts/anton/values.yaml) for the full configuration reference.
