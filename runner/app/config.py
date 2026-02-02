from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    github_token: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"
    context_path: str = "/app/context/task.json"
    work_dir: str = "/app/workspace"
    max_coder_turns: int = 15
    shell_timeout: int = 120
    max_review_rejections: int = 3
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
