"""Audio Ingress Daemon entrypoint for LiveKit WebRTC audio subscription."""

import asyncio
import logging
import signal
import sys

from packages.config.settings import settings
from packages.event_schema import RedisStreamBus
from services.audio_ingress.service import AudioIngressService
from services.audio_ingress.subscriber import LiveKitAudioSubscriber

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("audio_ingress")


async def main() -> None:
    """Runs the LiveKit Audio Ingress Daemon."""
    meeting_id = sys.argv[1] if len(sys.argv) > 1 else "default_meeting"
    logger.info("Starting Audio Ingress Daemon for meeting: %s", meeting_id)

    # 1. Initialize Redis Streams
    bus = RedisStreamBus()
    await bus.connect()

    # 2. Provision Audio Ingress Service & LiveKit Subscriber
    ingress_service = AudioIngressService(stream_bus=bus)
    subscriber = LiveKitAudioSubscriber(ingress_service=ingress_service)

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, shutting down audio ingress daemon...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        token = sys.argv[2] if len(sys.argv) > 2 else "dev_mock_token"
        await subscriber.subscribe_to_room(meeting_id=meeting_id, token=token)
        logger.info("Audio Ingress subscriber active. Awaiting audio frames...")
        await stop_event.wait()
    finally:
        await subscriber.unsubscribe_from_room(meeting_id)
        await bus.disconnect()
        logger.info("Audio Ingress Daemon cleanly shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Audio Ingress Daemon stopped by user.")
