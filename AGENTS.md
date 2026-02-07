# **AI Coding Agents Platform**

## **Overview**

This platform automates the software development lifecycle by autonomously resolving tasks from observability and project management tools. It uses a microservices architecture to ingest issues, reason about the best solution using LLMs, and execute fixes via ephemeral Kubernetes Jobs.

### **High-Level Architecture**

The system consists of three decoupled components:

1. **Ingester (The Gateway):** Securely receives and normalizes external webhooks.  
2. **Orchestrator (The Brain):** Decides *how* to solve a problem (Router) and manages the lifecycle of agents.  
3. **Agent Runner (The Worker):** An ephemeral K8S Job that clones the repo, implements the fix (Claude 3.5), validates it (GPT-4o), and submits a PR.

## ---

**1\. Component: Agent Ingester**

**Role:** The secure entry point for all external events. It acts as a "dumb pipe" to ensure speed, security, and standard formatting.

* **Tech Stack:** Python 3.14, FastAPI, Pydantic, RabbitMQ (aio\_pika).  
* **Responsibilities:**  
  * **Webhook Verification:** Validates HMAC signatures from JIRA/Datadog to prevent unauthorized access.  
  * **Normalization:** Converts varied payloads (Jira JSON, Datadog Alert JSON) into a standardized AgentTask internal model.  
  * **Buffering:** Publishes tasks to the agent\_events RabbitMQ exchange to handle burst traffic without dropping requests.  
* **Key Endpoints:**  
  * POST /webhooks/jira  
  * POST /webhooks/datadog  
  * POST /webhooks/sonar

## ---

**2\. Component: Orchestrator**

**Role:** The decision-making engine. It acts as the "Engineering Manager," analyzing the incoming task to select the right tools and risk profile before assigning work.

* **Tech Stack:** Python 3.14, Kubernetes Python Client, Anthropic API (Claude 3.5 Sonnet).  
* **Responsibilities:**  
  * **Consumer:** Listens to the orchestrator\_queue for new tasks.  
  * **The "Router" (LLM):** Sends the task context to Claude 3.5 to decide:  
    * Which **Template** to use (e.g., java-backend, react-frontend).  
    * Required **Skills** (e.g., "Needs access to AWS S3 docs").  
    * **Complexity** estimation.  
  * **Dispatcher:**  
    * Creates a ConfigMap containing the full task context (logs, description).  
    * Renders a Kubernetes Job manifest using Jinja2 templates.  
    * Submits the Job to the agents namespace.  
  * **Resilience:** Implements Dead Letter Queues (DLQ) for failed routing attempts.

## ---

**3\. Component: Agent Runner (K8S Job)**

**Role:** The "Software Engineer." It is an ephemeral container that runs for the duration of a single task and then destroys itself.

* **Tech Stack:** Python 3.14, LangChain / Raw LLM Clients, git, GitHub CLI (gh).  
* **Internal Workflow (The Loop):**  
  1. **Setup:** Clones the target repository and checks out a new branch fix/{task\_id}.  
  2. **Implementation (Claude 3.5 Sonnet):**  
     * Analyzes the codebase using **Tools** (read\_file, grep, ls).  
     * Edits files to apply the fix.  
     * **Self-Correction:** Runs tests (e.g., pytest, gradle test) to verify the fix works.  
  3. **Review (GPT-4o / o1):**  
     * Before committing, the agent generates a git diff.  
     * The diff is sent to a "Reviewer" model (GPT-4o) with the prompt: *"Find bugs, security issues, or bad practices."*  
     * **Outcome:**  
       * *REJECTED:* Feedback is sent back to Claude to fix.  
       * *APPROVED:* Proceed to submission.  
  4. **Submission:** Commits changes and uses gh pr create to open a Pull Request.

## ---

**Data Flow: Lifecycle of a Task**

1. **Trigger:** Datadog fires an alert: NullPointerException in PaymentService.java.  
2. **Ingest:**  
   * Ingester receives webhook.  
   * Validates secret.  
   * Converts to AgentTask(source=DATADOG, priority=P1).  
   * Publishes to RabbitMQ.  
3. **Route:**  
   * Orchestrator consumes message.  
   * Asks Claude: *"How do I fix this Java NPE?"*  
   * Claude replies: *"Use the java-backend template."*  
4. **Dispatch:**  
   * Orchestrator creates ConfigMap agent-ctx-123.  
   * Orchestrator applies Job/anton-runner-123.  
5. **Execute:**  
   * K8S Job starts.  
   * Agent clones repo.  
   * Agent identifies the null variable and adds a check.  
   * Agent runs mvn test \-\> **PASS**.  
   * Reviewer (GPT-4o) checks diff \-\> **APPROVED**.  
   * Agent opens PR: *"Fix NPE in PaymentService (Auto-Generated)"*.  
6. **Cleanup:** Kubernetes TTL controller deletes the finished Job pod.

## ---

**Configuration & Secrets**

The following Kubernetes Secrets must be present in the agents namespace:

| Secret Name | Key | Description |
| :---- | :---- | :---- |
| ai-secrets | anthropic\_api\_key | For the Orchestrator (Routing) and Agent (Coding). |
| ai-secrets | openai\_api\_key | For the Agent's "Reviewer" step. |
| github-secrets | pat | Personal Access Token for cloning repos and opening PRs. |
| webhook-secrets | secret\_token | Shared secret for validating incoming JIRA/Datadog webhooks. |
| broker-secrets | uri | RabbitMQ connection string (amqp://user:pass@host:5672). |

## **Monitoring**

* **Logs:** All components output structured JSON logs.  
* **Tracing:** The task\_id is generated at Ingestion and passed through to the Orchestrator and K8S Job logs for end-to-end traceability.  
* **Metrics:** RabbitMQ queue depth (orchestrator\_queue) indicates system load.
