from typing import Any

from app.models.agent_task import AgentTask, Priority, Source
from app.models.webhooks.jira import JiraWebhookPayload
from app.normalizers.base import BaseNormalizer

_PRIORITY_MAP: dict[str, Priority] = {
    "highest": Priority.P1,
    "critical": Priority.P1,
    "blocker": Priority.P1,
    "high": Priority.P2,
    "major": Priority.P2,
    "medium": Priority.P3,
    "normal": Priority.P3,
    "low": Priority.P4,
    "lowest": Priority.P4,
    "minor": Priority.P4,
    "trivial": Priority.P4,
}


class JiraNormalizer(BaseNormalizer):
    def normalize(self, raw: dict[str, Any]) -> AgentTask:
        payload = JiraWebhookPayload.model_validate(raw)
        priority_name = payload.issue.fields.priority.name.lower()
        return AgentTask(
            source=Source.JIRA,
            external_id=payload.issue.key or payload.issue.id,
            title=payload.issue.fields.summary,
            priority=_PRIORITY_MAP.get(priority_name, Priority.P3),
            raw_payload=raw,
        )
