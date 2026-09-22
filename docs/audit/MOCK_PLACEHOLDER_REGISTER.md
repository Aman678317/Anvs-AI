# ANVS-AI Multilingual Meeting Platform — Mock & Placeholder Register (Phase 0)

> **Document**: `docs/audit/MOCK_PLACEHOLDER_REGISTER.md`  
> **Author**: Lead Principal Software Engineer & QA Lead  
> **Date**: September 22, 2026  
> **Purpose**: Exhaustive catalog of all mock classes, synthetic tokens, placeholder stubs, and empty files, with remediation roadmap.

---

## 1. Classification of Mocks in ANVS-AI

Mocks in this codebase fall into two distinct categories:

1. **Acceptable Test Doubles**: Fallback mock engines (`MockSTTEngine`, `MockNMTEngine`, etc.) designed to allow unit tests and CI runners to execute rapidly without requiring 20GB+ of neural network weights or GPU hardware. These will be retained as test fixtures, but must never be permanently selected in production runtime environments.
2. **Unacceptable Production Placeholders**: Hardcoded fake tokens, empty worker directories, mock SFU provisioning, and empty test directories that mask missing functionality and prevent real media transmission. These must be replaced with real implementations.

---

## 2. Unacceptable Production Placeholders Register

| Location | Component | Type | Observed Mock / Placeholder | Production Requirement | Remediation PR |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `apps/web/src/app/page.tsx:98, 128` | Frontend Web Client | Fake Token | `livekitToken: "fake_lk_token_${newParticipantId}"`<br>`wsTicket: "ticket_${participantId}_${Date.now()}"` | Client must obtain real signed LiveKit JWT and WebSocket session ticket from API `/api/v1/rooms/join`. | **PR-14** |
| `apps/web/src/app/meeting/[id]/page.tsx:53` | Meeting Room Page | Fake Token | `livekitToken: "fake_lk_token_${generatedPid}"` | Real LiveKit token acquired via server session handshake. | **PR-14** |
| `apps/admin/src/context/AdminAuthContext.tsx:45, 53` | Admin Portal | Mock Token | `token: "mock_admin_bearer_token"` | Real admin JWT issued by `/auth/token` with verified `ADMIN` role. | **PR-14** |
| `services/api/services/livekit_service.py:79-98` | LiveKit SFU Service | Mock Method | `create_room` returns synthetic dictionary `{"sid": "RM_...", "status": "ACTIVE"}` without calling LiveKit SFU. `delete_room` returns `True`. | Real twirp/REST client using `livekit-api` package contacting LiveKit server. | **PR-05** |
| `services/voice-worker/` | Voice Cloning Worker | Empty Stub | Directory contains only a 48-byte empty `__init__.py`. | Full voice extraction and cloning worker daemon subscribing to Redis Streams. | **PR-11** |
| `apps/meeting-client/src/index.ts` | Meeting Client SDK | Stub Class | 40-line placeholder class `MeetingClient` with no WebRTC or WebSocket logic. | Full client SDK or consolidate directly into `apps/web/src/lib`. | **PR-14** |
| `tests/realtime/.gitkeep` | Realtime Test Suite | Empty Directory | Only `.gitkeep` exists. | Comprehensive tests for WebSocket connection lifecycle, caption fanout, and latency. | **PR-15** |
| `tests/security/.gitkeep` | Security Test Suite | Empty Directory | Only `.gitkeep` exists. | Automated tests for PostgreSQL RLS tenant isolation, token tampering, and RBAC bypass attempts. | **PR-15** |
| `tests/integration/.gitkeep` | Integration Test Suite | Empty Directory | Only `.gitkeep` exists. | End-to-end integration tests verifying multi-worker audio pipeline flow. | **PR-15** |

---

## 3. Acceptable Test Doubles (AI Fleet Engine Fallbacks)

Each AI worker currently provides a deterministic `Mock*Engine` implementing the corresponding abstract base class. These are used during unit tests and when local machine resources lack neural accelerators:

### 3.1 `MockSTTEngine` (`services/stt_worker/engine.py:44`)
- **Behavior**: Returns pre-canned transcript strings based on audio length or language tag.
- **Production Engine**: `FasterWhisperSTTEngine` (`Systran/faster-whisper-large-v3` or `medium.en`).
- **Policy**: Allowed in CI test suite; production config (`AI_STT_ENGINE=faster_whisper`) must fail fast if weights are unresolvable.

### 3.2 `MockNMTEngine` (`services/translation_worker/engine.py:49`)
- **Behavior**: Provides deterministic Spanish/French/German sample translations and passthrough for same-language pairs.
- **Production Engine**: `NLLBNMTEngine` (`facebook/nllb-200-distilled-600M` or IndicTrans2).
- **Policy**: Allowed in CI test suite; production config (`AI_TRANSLATION_ENGINE=nllb`) must load real translation models.

### 3.3 `MockTTSEngine` (`services/tts_worker/engine.py:32`)
- **Behavior**: Generates synthetic PCM sine waves matching target duration, embeds 20 kHz pilot tone.
- **Production Engine**: `PiperTTSEngine` (low-latency ONNX models) / `BarkTTSEngine`.
- **Policy**: Allowed in CI test suite; production config (`AI_TTS_ENGINE=piper`) must synthesize real phonemes.

### 3.4 `MockSpeakerEngine` (`services/speaker_worker/engine.py:41`)
- **Behavior**: Simulates speaker turns with synthetic speaker IDs (`speaker_0`, `speaker_1`).
- **Production Engine**: `PyAnnoteSpeakerEngine` (`pyannote/speaker-diarization-3.1`).
- **Policy**: Allowed in CI test suite; production config (`AI_SPEAKER_ENGINE=pyannote`) must compute real speaker embeddings.

### 3.5 `MockAssistantEngine` (`services/assistant_worker/engine.py:46`)
- **Behavior**: Uses regular expressions to detect keywords (`will`, `shall`, `todo`) and outputs synthetic summaries.
- **Production Engine**: `OpenAIAssistantEngine` or local `vLLM` / `Ollama` engine with PostgreSQL `pgvector` RAG search.
- **Policy**: Must be upgraded in **PR-12** with real vector semantic search and LLM completion.

---

## 4. Remediation Schedule

- **PR-01**: Clean duplicate hyphenated worker dirs, eliminate `ai-content-agent.db`.
- **PR-02**: Eliminate mock auth; connect `/auth/token` to database.
- **PR-05**: Implement real LiveKit SFU client in `services/api/services/livekit_service.py`.
- **PR-11**: Implement real `services/voice_worker/`.
- **PR-14**: Replace `fake_lk_token` and `mock_admin_bearer_token` in frontends with genuine backend tokens.
- **PR-15**: Populate `tests/realtime/`, `tests/security/`, and `tests/integration/` with production test suites.
