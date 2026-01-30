import asyncio
import logging

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage

from app.brain import TaskRouter
from app.config import settings
from app.dispatcher import JobManager
from app.models import AgentTask

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "agent_events"
ROUTING_KEY = "task.created"
QUEUE_NAME = "orchestrator_queue"
DLQ_EXCHANGE = "agent_events_dlq"
DLQ_QUEUE = "task.dlq"
RETRY_HEADER = "x-retry-count"


class Consumer:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._router = TaskRouter()
        self._dispatcher = JobManager()
        self._shutdown = asyncio.Event()

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)

        # Declare DLQ infrastructure
        dlq_exchange = await self._channel.declare_exchange(
            DLQ_EXCHANGE, ExchangeType.DIRECT, durable=True
        )
        dlq_queue = await self._channel.declare_queue(DLQ_QUEUE, durable=True)
        await dlq_queue.bind(dlq_exchange, routing_key=DLQ_QUEUE)

        # Declare main exchange & queue
        exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        queue = await self._channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange, routing_key=ROUTING_KEY)

        await queue.consume(self._on_message)
        logger.info(
            "Consumer started",
            extra={"queue": QUEUE_NAME, "routing_key": ROUTING_KEY},
        )

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        if self._shutdown.is_set():
            await message.nack(requeue=True)
            return

        retry_count = (message.headers or {}).get(RETRY_HEADER, 0)
        task_id = "unknown"

        try:
            task = AgentTask.model_validate_json(message.body)
            task_id = str(task.task_id)
            logger.info("Processing task", extra={"task_id": task_id, "retry": retry_count})

            plan = await self._router.route(task)
            self._dispatcher.create_job(task_id, plan, task)

            await message.ack()
            logger.info("Task completed", extra={"task_id": task_id})

        except Exception:
            logger.exception("Failed to process message", extra={"task_id": task_id, "retry": retry_count})

            if retry_count + 1 >= settings.max_retries:
                await self._send_to_dlq(message)
                await message.ack()
            else:
                await message.nack(requeue=False)
                await self._republish_with_retry(message, retry_count + 1)

    async def _republish_with_retry(
        self, original: AbstractIncomingMessage, new_count: int
    ) -> None:
        if self._channel is None:
            return
        exchange = await self._channel.get_exchange(EXCHANGE_NAME)
        headers = dict(original.headers or {})
        headers[RETRY_HEADER] = new_count
        await exchange.publish(
            aio_pika.Message(
                body=original.body,
                headers=headers,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=ROUTING_KEY,
        )
        logger.info(
            "Republished for retry",
            extra={"retry": new_count},
        )

    async def _send_to_dlq(self, message: AbstractIncomingMessage) -> None:
        if self._channel is None:
            return
        dlq_exchange = await self._channel.get_exchange(DLQ_EXCHANGE)
        await dlq_exchange.publish(
            aio_pika.Message(
                body=message.body,
                headers=dict(message.headers or {}),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=DLQ_QUEUE,
        )
        logger.warning(
            "Message sent to DLQ after max retries",
            extra={"max_retries": settings.max_retries},
        )

    async def shutdown(self) -> None:
        logger.info("Shutting down consumer...")
        self._shutdown.set()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("Consumer shut down")
