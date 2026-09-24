"""TTS Worker daemon entrypoint adhering to Document 14."""

import asyncio
import logging
import signal
import sys

from packages.config.settings import settings
from packages.event_schema import RedisStreamBus
from services.tts_worker.consumer import TTSConsumer
from services.tts_worker.egress import LiveKitAudioEgress
from services.tts_worker.engine import create_tts_engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tts_worker")


async def main() -> None:
    """Runs the TTS Worker daemon."""
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "default_meeting"
    logger.info("Initializing TTS Worker for meeting: %s", meeting_id)

    bus = RedisStreamBus()
    await bus.connect()

    egress = LiveKitAudioEgress()
    engine = create_tts_engine()
    consumer = TTSConsumer(stream_bus=bus, engine=engine, egress=egress)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, shutting down TTS worker...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    # On Windows, add_signal_handler might not be supported for all signals
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        await consumer.run(meeting_id=meeting_id, stop_event=stop_event)
    finally:
        await egress.close()
        await bus.disconnect()
        logger.info("TTS Worker disconnected from Redis bus.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("TTS Worker stopped by user.")
