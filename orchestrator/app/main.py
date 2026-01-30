import asyncio
import logging
import signal

from app.consumer import Consumer
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def main() -> None:
    consumer = Consumer()
    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        logger.info("Received shutdown signal")
        asyncio.ensure_future(consumer.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    await consumer.connect()
    logger.info("Orchestrator running — waiting for tasks")

    # Block until shutdown is signalled
    await consumer._shutdown.wait()


if __name__ == "__main__":
    asyncio.run(main())
