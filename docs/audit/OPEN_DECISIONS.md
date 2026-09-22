# ANVS-AI Multilingual Meeting Platform — Open Decisions (Phase 0)

> **Document**: `docs/audit/OPEN_DECISIONS.md`  
> **Author**: Lead Principal Software Engineer & Chief Architect  
> **Date**: September 22, 2026  
> **Status**: Approved Architectural Decisions for PR Execution

---

## 1. Overview

This document records the critical architectural and engineering decisions required to guide implementation through **PR-01 through PR-15**. Each decision evaluates options against the platform's core non-functional requirements:
- Sub-1500ms glass-to-glass latency.
- Strict multi-tenant isolation via PostgreSQL 16 Row Level Security (Invariant #1).
- Immutable lineage tracking (Invariant #2).
- Zero-echo acoustic watermarking (Invariant #3).
- Guaranteed poison pill quarantine (Invariant #4).

---

## 2. Architectural Decisions Register

### OD-01: AI Model Execution Profile for Local Development and CI vs Production

- **Context**: Real neural models (Faster-Whisper Large, NLLB-200 600M, PyAnnote 3.1, XTTS v2) require significant RAM (>12 GB) and CUDA GPUs to execute within SLA targets (<350ms STT, <250ms NMT). Developers and CI runners often run in CPU-only or restricted-memory environments.
- **Options**:
  1. *Require GPU everywhere*: Mandate CUDA 12+ and GPU runners for all environments.
  2. *Dual-Mode Architecture (Recommended)*:
     - **Production Mode (`AI_RUN_MODE=production`)**: Loads full quantized ONNX/TensorRT/PyTorch models (e.g. `faster-whisper-medium.en`, `nllb-200-distilled-600M`) on GPU. Fails immediately on startup if models or CUDA devices are unreachable.
     - **Dev/CI Mode (`AI_RUN_MODE=test` or `local_cpu`)**: Uses CPU-optimized quantized models (int8 / ONNX runtime) with automatic deterministic fallback to `Mock*Engine` when running unit tests or resource-constrained local environments.
- **Architectural Impact**: Preserves rapid CI execution and local developer velocity while guaranteeing zero mocks in production deployments. Enforced in `packages/config/settings.py` and worker factory functions.

---

### OD-02: Indic Language Translation Strategy (IndicTrans2 vs NLLB-200)

- **Context**: The platform targets 18 languages with high fidelity for South Asian enterprise markets (Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, etc.).
- **Options**:
  1. *NLLB-200 Distilled 600M only*: Unified single model covering 200 languages. Fast and compact, but lower BLEU/chrf scores on colloquial Indic dialects.
  2. *IndicTrans2 only*: Highest BLEU scores on 22 official Indian languages, but does not support European/East Asian languages.
  3. *Hybrid Translation Router (Recommended)*:
     - Use `IndicTrans2` (or quantized ONNX variant) when both source and target are Indic languages.
     - Use `NLLB-200` for cross-family language pairs (e.g. English <-> Hindi, Spanish <-> Japanese).
     - Standardize all internal representation on ISO 639-3 3-letter codes via `packages/language_registry`.
- **Architectural Impact**: Implemented in `services/translation_worker/engine.py` in **PR-09**.

---

### OD-03: Voice Cloning & Preservation Provider Architecture

- **Context**: `services/voice-worker` is currently a 48-byte empty stub. The architecture requires preserving speaker vocal characteristics across translated synthetic speech while adhering to ethical consent constraints.
- **Options**:
  1. *Third-Party Cloud API (ElevenLabs / Cartesia)*: High quality, but introduces external network latency (>400ms), SaaS costs, and data residency compliance challenges.
  2. *Coqui XTTS v2 / F5-TTS Self-Hosted (Recommended)*:
     - Open-source, self-hosted inside Kubernetes worker cluster.
     - 3-second reference audio slice extracted during user's first speech turn.
     - Generates 256-dimensional speaker embedding stored in `voice_profiles` table.
     - Enforces explicit user consent flag (`voice_clone_consent: true`) before activation. If consent is false, falls back to neutral gender-matched Piper TTS voice.
- **Architectural Impact**: Implemented in `services/voice_worker/` and `packages/database/models/voice_profile.py` in **PR-03** and **PR-11**.

---

### OD-04: Audio Ingress Integration Pattern (LiveKit SFU to Audio Ingestion)

- **Context**: Browsers publish WebRTC audio tracks to LiveKit SFU. How does the backend AI pipeline capture raw participant PCM audio for STT and VAD?
- **Options**:
  1. *LiveKit Egress Service to Redis/RTMP*: Standard LiveKit egress, but designed for recording/streaming rather than sub-200ms real-time audio chunking.
  2. *Headless WebRTC Ingress Worker Daemon (`services/audio_ingress`) using LiveKit Python SDK (Recommended)*:
     - A dedicated Python service (`services/audio_ingress/`) joins each active meeting as an automated bot participant (`canPublish: false`, `canSubscribe: true`).
     - Subscribes to all incoming participant audio tracks via WebRTC.
     - Feeds PCM frames directly into `packages/audio/ingestion.py:AudioIngestionPipeline`.
     - Filters out 20 kHz watermarked synthetic audio immediately (Invariant #3).
     - Resamples 48kHz -> 16kHz and pushes speech chunks into Redis Stream `meeting:{id}:audio`.
- **Architectural Impact**: Implemented in **PR-05** and **PR-06**.

---

### OD-05: Meeting Client Package Architecture (`apps/meeting-client`)

- **Context**: `apps/meeting-client` is a 40-line stub. `apps/web` is a Next.js 14 application with direct React components.
- **Options**:
  1. *Monolithic Client in `apps/web`*: Delete `apps/meeting-client` and write all WebRTC/WebSocket logic directly into `apps/web/src/lib/`.
  2. *Shared TypeScript SDK Package in `packages/meeting-client` (Recommended)*:
     - Move and complete the client SDK as an isomorphic package `@multilingual/meeting-client` in `packages/meeting-client/`.
     - Encapsulates WebSocket connection lifecycle, ticket handshake, caption subscription, reconnection backoff, and LiveKit track management.
     - Consumed cleanly by both `apps/web` (meeting participant client) and future client platforms (Electron, React Native, Headless bots).
- **Architectural Impact**: Implemented in **PR-04** and **PR-14**.
