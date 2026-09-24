# ADR-001: LiveKit Server-Side Audio Track Publication Architecture

- **Status**: Accepted (DEC-02)
- **Date**: 2026-09-24
- **Deciders**: Platform Architecture Team, Real-Time Media Core
- **Consulted**: `services/tts_worker/egress.py`, `services/api/services/livekit_service.py`
- **Related ADRs**: [ADR-002: Piper vs XTTS Speech Synthesis Engine](ADR-002-piper-vs-xtts.md)

---

## Context and Problem Statement

In the ANVS-AI real-time translation pipeline, synthesized target-language speech must be delivered back into the meeting room as synchronized WebRTC audio. Previously, audio egress was simulated in memory by counting 20ms chunks without publishing real WebRTC tracks to LiveKit SFU.

To satisfy **Invariant #3** and production requirements, synthesized audio must be published onto real LiveKit tracks with lowest possible latency (<50ms delivery overhead), while supporting multi-language fan-out and multi-tenant isolation.

## Decision Drivers

1. Direct frame-level control over 20ms WebRTC chunks and 20 kHz ultrasonic watermark verification.
2. Latency budget: end-to-end speak-to-playable latency must stay within 1.5s–2.5s.
3. Resource efficiency: avoid spinning up separate heavyweight RTMP/GStreamer processes per language.
4. Clean separation between production strictness (fail-fast on SFU disconnect) and local test simulation.

## Considered Options

- **Option A**: Dedicated persistent bot participant per meeting (`bot_translator_<target_language>`) joining via `livekit.rtc`, provisioning an `AudioSource` + `LocalAudioTrack`, and pushing frames directly.
- **Option B**: External GStreamer/RTMP egress pipeline piping audio through virtual ALSA loopback devices.
- **Option C**: Client-side peer-to-peer data channel streaming of raw PCM chunks for playback in Web Audio API.

## Decision Outcome

**Chosen Option: Option A**

The platform standardizes on persistent per-meeting bot participants joining via native `livekit.rtc`:

1. **Single Publishing Path**: Handled exclusively in [`services/tts_worker/egress.py`](../../services/tts_worker/egress.py) by `LiveKitAudioEgress`.
2. **Dedicated Track Ownership**: The bot participant connects to `room_{meeting_id}`, provisions an `AudioSource(sample_rate=48000, num_channels=1)`, and publishes a `LocalAudioTrack` named `live_translation_{target_language}`.
3. **Graceful Fallback Outside Production**: When running in development or unit tests without an active LiveKit server, the engine degrades to a simulated metrics tracker. In production (`APP_ENV=production`), any connection or publishing failure immediately raises `ConnectionError`.

## Implementation References

- Egress Implementation: [`services/tts_worker/egress.py`](../../services/tts_worker/egress.py)
- Integration Verification: [`tests/integration/test_egress_live_livekit.py`](../../tests/integration/test_egress_live_livekit.py)
- Settings Configuration: [`packages/config/settings.py`](../../packages/config/settings.py)
