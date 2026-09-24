"""Voice Cloning Worker daemon entrypoint adhering to Document 14 (PR-11)."""

import asyncio
import logging
import signal
import sys

from packages.config.settings import settings
from packages.event_schema import RedisStreamBus
from services.voice_worker.consumer import VoiceWorkerConsumer
from services.voice_worker.engine import create_voice_engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voice_worker")


async def main() -> None:
    """Runs the Voice Cloning Worker daemon."""
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "default_meeting"
    logger.info("Initializing Voice Cloning Worker for meeting: %s", meeting_id)

    bus = RedisStreamBus()
    await bus.connect()

    engine = create_voice_engine()
    consumer = VoiceWorkerConsumer(stream_bus=bus, engine=engine)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, shutting down voice worker...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    # On Windows, add_signal_handler may not be available for all signals
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        await consumer.run(meeting_id=meeting_id, stop_event=stop_event)
    finally:
        await bus.disconnect()
        logger.info("Voice Cloning Worker disconnected from Redis bus.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Voice Cloning Worker stopped by user.")
