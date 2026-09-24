"""Assistant RAG Worker daemon entrypoint adhering to Document 14."""

import asyncio
import logging
import signal
import sys

from packages.config.settings import settings
from packages.event_schema import RedisStreamBus
from services.assistant_worker.consumer import AssistantConsumer
from services.assistant_worker.engine import create_assistant_engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("assistant_worker")


async def main() -> None:
    """Runs the Assistant RAG Worker daemon."""
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "default_meeting"
    logger.info("Initializing Assistant RAG Worker for meeting: %s", meeting_id)

    bus = RedisStreamBus()
    await bus.connect()

    engine = create_assistant_engine()
    consumer = AssistantConsumer(stream_bus=bus, engine=engine)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, shutting down Assistant worker...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        await consumer.run(meeting_id=meeting_id, stop_event=stop_event)
    finally:
        await bus.disconnect()
        logger.info("Assistant Worker disconnected from Redis bus.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Assistant Worker stopped by user.")
