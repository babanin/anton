from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# --- Ingested task (mirrors the Ingester's AgentTask) ---


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
    task_id: UUID
    source: Source
    external_id: str
    title: str
    priority: Priority
    raw_payload: dict[str, Any]
    created_at: datetime


# --- Router output (LLM decision) ---


class TemplateId(str, Enum):
    JAVA_BACKEND = "java-backend"
    PYTHON_BACKEND = "python-backend"
    REACT_FRONTEND = "react-frontend"
    GENERAL_RESEARCH = "general-research"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RouterPlan(BaseModel):
    template_id: TemplateId
    complexity: Complexity
    required_skills: list[str] = Field(default_factory=list)
    context_summary: str
