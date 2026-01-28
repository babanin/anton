from pydantic import BaseModel


class SonarQualityGate(BaseModel):
    status: str = ""

    model_config = {"extra": "allow"}


class SonarTask(BaseModel):
    id: str = ""
    status: str = ""

    model_config = {"extra": "allow"}


class SonarProject(BaseModel):
    key: str = ""
    name: str = ""

    model_config = {"extra": "allow"}


class SonarWebhookPayload(BaseModel):
    taskId: str = ""
    status: str = ""
    qualityGate: SonarQualityGate = SonarQualityGate()
    project: SonarProject = SonarProject()

    model_config = {"extra": "allow"}
