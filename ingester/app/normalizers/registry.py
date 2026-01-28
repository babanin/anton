from app.models.agent_task import Source
from app.normalizers.base import BaseNormalizer
from app.normalizers.datadog import DatadogNormalizer
from app.normalizers.jira import JiraNormalizer
from app.normalizers.sonar import SonarNormalizer

_REGISTRY: dict[Source, type[BaseNormalizer]] = {
    Source.JIRA: JiraNormalizer,
    Source.DATADOG: DatadogNormalizer,
    Source.SONARCLOUD: SonarNormalizer,
}

_INSTANCES: dict[Source, BaseNormalizer] = {}


def get_normalizer(source: Source) -> BaseNormalizer:
    if source not in _INSTANCES:
        _INSTANCES[source] = _REGISTRY[source]()
    return _INSTANCES[source]
