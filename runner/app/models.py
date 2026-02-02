from pydantic import BaseModel


class TaskConfig(BaseModel):
    repo_url: str
    task_description: str
    issue_id: str


class ReviewResult(BaseModel):
    approved: bool
    reason: str
