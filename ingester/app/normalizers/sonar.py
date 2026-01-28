from typing import Any

from app.models.agent_task import AgentTask, Priority, Source
from app.models.webhooks.sonar import SonarWebhookPayload
from app.normalizers.base import BaseNormalizer

_GATE_STATUS_MAP: dict[str, Priority] = {
    "error": Priority.P2,
    "warn": Priority.P3,
    "ok": Priority.P4,
}


class SonarNormalizer(BaseNormalizer):
    def normalize(self, raw: dict[str, Any]) -> AgentTask:
        payload = SonarWebhookPayload.model_validate(raw)

        task_status = payload.status.upper()
        if task_status in ("FAILED", "CANCELLED"):
            priority = Priority.P1
        else:
            gate = payload.qualityGate.status.lower()
            priority = _GATE_STATUS_MAP.get(gate, Priority.P3)

        return AgentTask(
            source=Source.SONARCLOUD,
            external_id=payload.taskId or payload.project.key,
            title=f"SonarCloud analysis: {payload.project.name or payload.project.key}",
            priority=priority,
            raw_payload=raw,
        )
