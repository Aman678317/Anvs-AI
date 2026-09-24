# ADR-002: Piper ONNX Default vs XTTS-v2 Speech Synthesis Engine

- **Status**: Proposed (DEC-03)
- **Date**: 2026-09-24
- **Deciders**: AI Core & Performance Team
- **Consulted**: `services/tts_worker/engine.py`, `packages/config/settings.py`
- **Related ADRs**: [ADR-001: LiveKit Server-Side Audio Track Publication Architecture](ADR-001-livekit-bot-publication.md)

---

## Context and Problem Statement

The speech synthesis layer converts translated text into natural audio for listener playback. Two primary model families were evaluated:

1. **Coqui XTTS-v2**: Autoregressive neural voice cloning with ~4GB VRAM footprint per worker, ~800ms time-to-first-chunk latency, and an archived upstream repository.
2. **Piper TTS**: Fast local neural text-to-speech optimized for ONNX Runtime with CPU/GPU execution, <150ms synthesis latency, and 40+ supported languages.

Meeting participants require real-time playback (<2.5s total loop latency) under high multi-tenant concurrency.

## Decision Drivers

1. Meeting latency budget: total STT -> NMT -> TTS time must remain $\le 2000$ ms.
2. Cost & infrastructure footprint: running multiple concurrent translations per meeting must not require dedicated GPU hardware for every language.
3. Voice cloning capabilities: high-fidelity zero-shot voice cloning should remain accessible when explicit user consent is provided.

## Decision Outcome

**Chosen Path: Piper Default with XTTS-v2 Upgrade Path (Option A)**

1. **Default Production Engine**: Standardize on **Piper ONNX** for streaming speech synthesis in real-time meetings. Piper delivers <150ms first-chunk synthesis with minimal CPU/GPU overhead.
2. **Unified Engine Interface**: Both engines implement the canonical `BaseTTSEngine` in [`services/tts_worker/engine.py`](../../services/tts_worker/engine.py).
3. **Optional XTTS-v2 Path**: XTTS-v2 is retained as an opt-in premium voice-cloning path triggered when a participant has signed a voice profile consent record in PostgreSQL (`voice_profiles` table).
4. **Invariant #3 Guarantee**: In both engines, 20 kHz ultrasonic watermarking is strictly injected via `packages/audio/watermark.py` before audio egress.

## Implementation References

- TTS Engine: [`services/tts_worker/engine.py`](../../services/tts_worker/engine.py)
- Settings & Selection: [`packages/config/settings.py`](../../packages/config/settings.py)
- Latency Budget Verification: [`scripts/ci_latency_budget.py`](../../scripts/ci_latency_budget.py)
