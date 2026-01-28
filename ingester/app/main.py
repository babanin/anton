import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routers import datadog, health, jira, sonar
from app.logging_config import setup_logging
from app.services.publisher import RabbitMQPublisher

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    publisher = RabbitMQPublisher()
    await publisher.connect()
    app.state.publisher = publisher
    logger.info("Agent Ingester started")
    yield
    await publisher.disconnect()
    logger.info("Agent Ingester stopped")


app = FastAPI(title="Agent Ingester", lifespan=lifespan)

app.include_router(health.router)
app.include_router(jira.router)
app.include_router(datadog.router)
app.include_router(sonar.router)
