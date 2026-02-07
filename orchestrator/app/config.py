from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://rabbit:rabbit@rabbitmq:5672/"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    k8s_namespace: str = "agents"
    agent_image: str = "anton-runner:latest"
    max_retries: int = 3
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
