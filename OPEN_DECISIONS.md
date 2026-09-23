# ANVS-AI Multilingual Meeting Platform — Open Decisions Register (Stage 0)

> **Document Version**: 4.0.0  
> **Status**: Active Architectural & Operational Review  
> **Guiding Principle**: Do not silently invent solutions. Explicitly catalog open decisions with options, trade-offs, and recommended paths.

---

## 1. Architectural & Model Decision Ledger

### DEC-01: Meta NLLB-200 vs IndicTrans2 for Indic Language Pairs

- **Context**: Meta's NLLB-200 distilled 600M covers 196 languages with research-oriented licensing. AI4Bharat's IndicTrans2 (1B) achieves state-of-the-art BLEU/chrF++ scores on Indian language pairs (Hindi, Marathi, Tamil, Bengali, Telugu, Gujarati, Kannada, etc.).
- **Options**:
  1. _Option A_: Use NLLB-200 for global European/Asian pairs (es, fr, de, ja, zh) and specialized IndicTrans2 for Indian language directions (hi, mr, ta, te).
  2. _Option B_: Standardize exclusively on NLLB-200 for all 200 languages.
- **Recommended Path**: **Option A**. The capability registry should support provider-neutral model selection per language pair, routing Indic directions to IndicTrans2 for superior colloquial accuracy and technical term preservation.
- **Status**: **PROPOSED FOR PR-11**.

### DEC-02: LiveKit Server-Side Track Publication Implementation

- **Context**: LiveKit audio egress requires publishing synthesized watermarked audio into room tracks. Merely counting frames in Python memory is insufficient (PDF Section 11).
- **Options**:
  1. _Option A_: Use the official Python `livekit` and `livekit.rtc` package: join the room as a headless bot participant (`identity="bot_translator_en"`), initialize an `AudioSource`, create a `LocalAudioTrack`, and push 20ms PCM frames.
  2. _Option B_: Use LiveKit Egress/Ingress service via RTMP/GStreamer.
- **Recommended Path**: **Option A**. Joining as a dedicated server-side bot participant with an `AudioSource` provides direct programmatic frame-level control, lowest latency (<50ms pipeline overhead), and audience-scoped track subscription metadata.
- **Status**: **PROPOSED FOR PR-12**.

### DEC-03: Piper ONNX vs Coqui XTTS-v2 for Production Speech Synthesis

- **Context**: Settings currently default to `coqui/XTTS-v2`. Coqui's open-source repository is archived, and XTTS-v2 has high GPU VRAM consumption (~4GB per worker) with ~800ms first-chunk latency. Piper TTS is ONNX-based, executes in <150ms on CPU/GPU, and supports 40+ languages.
- **Options**:
  1. _Option A_: Standardize on Piper ONNX as the primary real-time TTS engine, using XTTS-v2 strictly for optional high-fidelity voice cloning when requested with user consent.
  2. _Option B_: Retain XTTS-v2 as the only engine.
- **Recommended Path**: **Option A**. Piper ONNX guarantees the 1.5s–2.5s end-to-end latency budget and high concurrency without requiring prohibitive multi-GPU infrastructure.
- **Status**: **PROPOSED FOR PR-12**.

### DEC-04: Nyquist-Compliant Ultrasonic Watermark Detection Strategy

- **Context**: Live WebRTC incoming audio arrives at 48,000 Hz. STT models (Whisper) require 16,000 Hz. The ultrasonic watermark is embedded at 20,000 Hz.
- **Invariant Rule**: The Nyquist frequency of 16,000 Hz audio is 8,000 Hz. If incoming audio is downsampled from 48 kHz to 16 kHz _before_ watermark inspection, the 20 kHz ultrasonic tone is mathematically destroyed (or aliases into audible bands), breaking Invariant #3 loop rejection!
- **Decision**: In `AudioIngestionPipeline`, watermark detection MUST execute at the native 48,000 Hz sample rate on the raw incoming frames _before_ the polyphase resampler converts to 16,000 Hz for VAD and STT.
- **Status**: **CONFIRMED & PRESERVED IN CODE**.

### DEC-05: Seven-Type Memory Layer Scope & Retention Policy

- **Context**: The PDF integrates a Seven-Type Memory Architecture (Working, Semantic, Episodic, Procedural, Retrieval, Parametric, Prospective) as an optional agent layer for context and operational intelligence.
- **Constraints**:
  1. Memory must never feed synthetic audio back into live source STT.
  2. In-context working memory must be bounded to the active meeting window (sliding 10–20 segments).
  3. Durable episodic memory (meeting summaries, action items) requires explicit user/host consent and tenant-isolated storage with expiration rules.
- **Recommended Path**: Implement the Memory Orchestrator in `services/assistant_worker/` strictly as a retrieval and ranking layer for Copilot Q&A and post-meeting recaps, never as a bypass into the live streaming translation pipeline.
- **Status**: **PROPOSED FOR PR-14**.

### DEC-06: Production Configuration & Fail-Fast Mock Policy

- **Context**: Settings currently allow `"mock"` as defaults for all AI workers.
- **Decision**: In `packages/config/settings.py`, if `APP_ENV == "production"` and any worker engine is configured as `"mock"`, the service must raise `RuntimeError("Production cannot boot with mock engine defaults")` during lifespan startup, preventing silent fallback to fake output.
- **Status**: **PROPOSED FOR PR-01 / PR-15**.
