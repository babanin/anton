from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    webhook_secret: str = "changeme-in-production"
    rabbitmq_url: str = "amqp://rabbit:rabbit@rabbitmq:5672/"
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
