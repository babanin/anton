from typing import Any

from pydantic import BaseModel


class JiraPriority(BaseModel):
    name: str = "Medium"

    model_config = {"extra": "allow"}


class JiraFields(BaseModel):
    summary: str = ""
    priority: JiraPriority = JiraPriority()

    model_config = {"extra": "allow"}


class JiraIssue(BaseModel):
    id: str = ""
    key: str = ""
    fields: JiraFields = JiraFields()

    model_config = {"extra": "allow"}


class JiraWebhookPayload(BaseModel):
    webhookEvent: str = ""
    issue: JiraIssue = JiraIssue()

    model_config = {"extra": "allow"}
