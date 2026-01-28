from pydantic import BaseModel


class DatadogWebhookPayload(BaseModel):
    id: str = ""
    title: str = ""
    alert_priority: str = ""
    alert_status: str = ""

    model_config = {"extra": "allow"}
