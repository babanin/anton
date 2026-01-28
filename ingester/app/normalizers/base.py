from abc import ABC, abstractmethod
from typing import Any

from app.models.agent_task import AgentTask


class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> AgentTask: ...
