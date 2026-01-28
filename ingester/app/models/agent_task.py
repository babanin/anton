from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Source(str, Enum):
    JIRA = "jira"
    DATADOG = "datadog"
    SONARCLOUD = "sonarcloud"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class AgentTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    source: Source
    external_id: str
    title: str
    priority: Priority
    raw_payload: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
