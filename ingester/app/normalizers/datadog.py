from typing import Any

from app.models.agent_task import AgentTask, Priority, Source
from app.models.webhooks.datadog import DatadogWebhookPayload
from app.normalizers.base import BaseNormalizer

_PRIORITY_MAP: dict[str, Priority] = {
    "p1": Priority.P1,
    "p2": Priority.P2,
    "p3": Priority.P3,
    "p4": Priority.P4,
}

_STATUS_MAP: dict[str, Priority] = {
    "triggered": Priority.P1,
    "warn": Priority.P2,
    "no data": Priority.P3,
    "recovered": Priority.P4,
}


class DatadogNormalizer(BaseNormalizer):
    def normalize(self, raw: dict[str, Any]) -> AgentTask:
        payload = DatadogWebhookPayload.model_validate(raw)

        priority = Priority.P3
        if payload.alert_priority:
            priority = _PRIORITY_MAP.get(
                payload.alert_priority.lower(), Priority.P3
            )
        elif payload.alert_status:
            priority = _STATUS_MAP.get(
                payload.alert_status.lower(), Priority.P3
            )

        return AgentTask(
            source=Source.DATADOG,
            external_id=payload.id,
            title=payload.title,
            priority=priority,
            raw_payload=raw,
        )
