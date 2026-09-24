"""Compose/CI smoke test: assert PCM actually reaches Redis (P0 runtime wiring).

Runs inside the ``smoke`` profile service of ``docker-compose.prod.yml``:

1. Feeds 2 seconds of synthesized *human* speech (voiced, no 20 kHz watermark)
   through :class:`AudioIngressService` connected to the real Redis container.
2. Asserts the source-segment stream depth
   (``XLEN events:meeting:<MEETING_ID>:audio``) becomes > 0 — i.e. voiced
   segments were published onto the stream consumed by the STT fleet.
3. Feeds watermarked (synthetic TTS-style) audio back through the same
   ingress path and asserts it is dropped (Invariant #3 loop rejection):
   the stream depth must not grow.

Exits non-zero on any failed assertion so docker compose / CI can gate on it.
"""

import asyncio
import os
import sys
import time

import numpy as np

from packages.audio.watermark import embed_watermark
from packages.config.settings import settings
from packages.event_schema import STREAM_AUDIO, RedisStreamBus, get_stream_key
from services.audio_ingress.service import AudioIngressService

MEETING_ID = os.environ.get("MEETING_ID", "smoke_meeting")
SR = 48000


def _to_pcm16(samples: np.ndarray) -> bytes:
    return (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def _human_speech(seconds: float = 2.0) -> np.ndarray:
    """Synthesized voiced speech-band waveform WITHOUT the 20 kHz watermark."""
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    speech = 0.5 * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 660 * t))
    return speech.astype(np.float32)


def _watermarked_speech(seconds: float = 1.0) -> np.ndarray:
    """TTS-style output: speech band plus the embedded 20 kHz ultrasonic pilot."""
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    speech = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    return embed_watermark(speech, sample_rate=SR, watermark_freq=20000.0)


async def main() -> int:
    bus = RedisStreamBus()
    await bus.connect()
    stream_key = get_stream_key(MEETING_ID, STREAM_AUDIO)
    try:
        await bus.client.delete(stream_key)
        service = AudioIngressService(stream_bus=bus, source_sample_rate=SR)
        chunk_samples = SR // 10  # 100ms ingest chunks

        async def feed(samples: np.ndarray, participant: str) -> None:
            for i in range(0, len(samples), chunk_samples):
                chunk = samples[i : i + chunk_samples]
                await service.ingest_audio_pcm(
                    MEETING_ID, participant, _to_pcm16(chunk)
                )
                await asyncio.sleep(0.005)
            await service.stop_track(MEETING_ID, participant)

        # 1. Human speech must produce voiced segments that reach Redis.
        deadline = time.monotonic() + 15.0
        depth = 0
        while time.monotonic() < deadline:
            await feed(_human_speech(), "smoke_speaker")
            depth = await bus.get_stream_length(stream_key)
            if depth > 0:
                print(f"SMOKE PASS: PCM reached Redis, {stream_key} depth={depth}")
                break
            await asyncio.sleep(0.25)
        else:
            print(f"SMOKE FAIL: {stream_key} depth stayed 0 — no PCM in Redis")
            return 1

        # 2. Invariant #3: watermarked (synthetic) audio fed back must be dropped.
        before = depth
        await feed(_watermarked_speech(), "loopback_speaker")
        after = await bus.get_stream_length(stream_key)
        stats = service.get_metrics()
        if after != before or stats["watermarked_frames_dropped"] <= 0:
            print(
                f"SMOKE FAIL: Invariant #3 violated — depth {before}->{after}, "
                f"dropped={stats['watermarked_frames_dropped']}"
            )
            return 1
        print(
            "SMOKE PASS: Invariant #3 loop rejection held "
            f"(dropped={stats['watermarked_frames_dropped']} watermarked frames)"
        )
        return 0
    finally:
        await bus.disconnect()


if __name__ == "__main__":
    if settings.app_env.lower() in ("production", "prod"):
        print("Smoke harness must run with APP_ENV=development")
        sys.exit(2)
    sys.exit(asyncio.run(main()))
