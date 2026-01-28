import logging

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.config import settings

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "agent_events"
ROUTING_KEY = "task.created"


class RabbitMQPublisher:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        logger.info("Connected to RabbitMQ", extra={"exchange": EXCHANGE_NAME})

    async def disconnect(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

    async def publish(self, body: bytes) -> None:
        if self._exchange is None:
            raise RuntimeError("Publisher not connected")
        message = Message(
            body,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self._exchange.publish(message, routing_key=ROUTING_KEY)
        logger.info("Published message", extra={"routing_key": ROUTING_KEY})

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed
