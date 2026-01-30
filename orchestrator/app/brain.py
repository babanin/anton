import json
import logging

import anthropic

from app.config import settings
from app.models import AgentTask, RouterPlan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a Technical Lead. Analyze this task and decide which agent "
    "template to use.\n\n"
    "You MUST respond with a single JSON object (no markdown fences) "
    "containing exactly these fields:\n"
    '- "template_id": one of "java-backend", "python-backend", '
    '"react-frontend", "general-research"\n'
    '- "complexity": one of "low", "medium", "high"\n'
    '- "required_skills": a list of short skill strings '
    '(e.g. ["django", "sql", "aws"])\n'
    '- "context_summary": a concise, sanitized summary of the task '
    "for the executing agent\n"
)


class TaskRouter:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def route(self, task: AgentTask) -> RouterPlan:
        task_id = str(task.task_id)
        logger.info("Routing task via LLM", extra={"task_id": task_id})

        user_content = (
            f"Source: {task.source.value}\n"
            f"Priority: {task.priority.value}\n"
            f"Title: {task.title}\n"
            f"External ID: {task.external_id}\n"
            f"Payload:\n{json.dumps(task.raw_payload, indent=2, default=str)}"
        )

        response = await self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text.strip()
        logger.debug("LLM raw response", extra={"task_id": task_id, "raw": raw_text})

        plan = RouterPlan.model_validate_json(raw_text)
        logger.info(
            "Task routed",
            extra={
                "task_id": task_id,
                "template_id": plan.template_id.value,
                "complexity": plan.complexity.value,
            },
        )
        return plan
