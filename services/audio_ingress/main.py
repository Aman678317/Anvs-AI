"""Audio Ingress Daemon entrypoint for LiveKit WebRTC audio subscription.

Runtime wiring (P0): this module is the container entrypoint referenced by
``services/audio_ingress/Dockerfile`` and the ``audio-ingress`` service in
``docker-compose.prod.yml``. It runs as a headless watcher bot that:

1. Discovers active meeting rooms via the control-plane API
   (``GET /api/v1/rooms/active``, bearer token from ``INGRESS_API_TOKEN``)
   when configured, or falls back to the single room given by ``MEETING_ID``.
2. Mints its own subscribe-only LiveKit access token locally (HS256 JWT with
   the ``LIVEKIT_API_KEY``/``LIVEKIT_API_SECRET`` pair) so it never needs a
   human join token.
3. Joins each room as identity ``bot_audio_ingress`` and pipes subscribed
   human PCM tracks into :class:`AudioIngressService`, which enforces the
   Invariant #3 watermark gate and publishes voiced segments onto the Redis
   ``audio`` stream consumed by the STT fleet.
"""

import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import time

import httpx
from jose import jwt

from packages.config.settings import settings
from packages.event_schema import STREAM_AUDIO, RedisStreamBus, get_stream_key
from services.audio_ingress.service import AudioIngressService
from services.audio_ingress.subscriber import LiveKitAudioSubscriber

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("audio_ingress")

DISCOVERY_INTERVAL_SEC = float(os.environ.get("INGRESS_DISCOVERY_INTERVAL_SEC", "10"))
API_BASE_URL = os.environ.get("INGRESS_API_URL", "").rstrip("/")
API_TOKEN = os.environ.get("INGRESS_API_TOKEN", "")


def generate_watcher_token(meeting_id: str, ttl_seconds: int = 3600) -> str:
    """Mints a subscribe-only LiveKit access token for the watcher bot identity."""
    now = int(time.time())
    claims = {
        "iss": settings.livekit_api_key,
        "sub": "bot_audio_ingress",
        "name": "Audio Ingress Watcher Bot",
        "nbf": now - 5,
        "exp": now + ttl_seconds,
        "video": {
            "room": f"room_{meeting_id}",
            "roomJoin": True,
            "canPublish": False,
            "canSubscribe": True,
            "canPublishData": False,
        },
    }
    token: str = jwt.encode(claims, settings.livekit_api_secret, algorithm="HS256")
    return token


async def discover_active_meetings() -> list[str]:
    """Queries the control plane for currently active meeting IDs.

    Returns an empty list when discovery is not configured (no API URL/token),
    letting the caller fall back to the static MEETING_ID env var.
    """
    if not API_BASE_URL or not API_TOKEN:
        return []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{API_BASE_URL}/api/v1/rooms/active",
                headers={"Authorization": f"Bearer {API_TOKEN}"},
            )
            if resp.status_code != 200:
                logger.warning(
                    "Meeting discovery returned HTTP %s from %s", resp.status_code, API_BASE_URL
                )
                return []
            data = resp.json()
            meetings = data if isinstance(data, list) else data.get("meetings", [])
            return [
                str(m["meeting_id"]) for m in meetings if isinstance(m, dict) and "meeting_id" in m
            ]
    except Exception as exc:
        logger.warning("Meeting discovery failed: %s", exc)
        return []


async def main() -> None:
    """Runs the LiveKit Audio Ingress watcher daemon until terminated."""
    static_meeting_id = sys.argv[1] if len(sys.argv) > 1 else settings.meeting_id
    logger.info(
        "Starting Audio Ingress Daemon (static fallback meeting=%s, discovery=%s)",
        static_meeting_id,
        "enabled" if API_BASE_URL and API_TOKEN else "disabled",
    )

    bus = RedisStreamBus()
    await bus.connect()

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

    joined: set[str] = set()
    try:
        while not stop_event.is_set():
            targets = await discover_active_meetings()
            if not targets:
                targets = [static_meeting_id]

            for meeting_id in targets:
                if meeting_id in joined:
                    continue
                try:
                    token = generate_watcher_token(meeting_id)
                    await subscriber.subscribe_to_room(meeting_id=meeting_id, token=token)
                    joined.add(meeting_id)
                    logger.info("Watcher bot joined room for meeting %s", meeting_id)
                except Exception as exc:
                    logger.error("Failed to join room for meeting %s: %s", meeting_id, exc)
                    if settings.app_env.lower() in ("production", "prod"):
                        raise

            # Periodic health telemetry (source-segment stream depth proves
            # PCM is actually flowing end-to-end into Redis).
            depths = {
                m: await bus.get_stream_length(get_stream_key(m, STREAM_AUDIO)) for m in joined
            }
            logger.info(
                "Ingress heartbeat: rooms=%d audio_stream_depth=%s metrics=%s",
                len(joined),
                json.dumps(depths),
                subscriber.get_metrics(),
            )

            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=DISCOVERY_INTERVAL_SEC)
    finally:
        for meeting_id in list(joined):
            await subscriber.unsubscribe_from_room(meeting_id)
        await bus.disconnect()
        logger.info("Audio Ingress Daemon cleanly shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Audio Ingress Daemon stopped by user.")
