# ANVS-AI Multilingual Meeting Platform — Implementation Map (Phase 0)

> **Document**: `docs/audit/IMPLEMENTATION_MAP.md`  
> **Author**: Lead Principal Software Engineer & Architecture Team  
> **Date**: September 22, 2026  
> **Purpose**: Detailed technical roadmap mapping every existing repository component to the PR-01 through PR-15 execution units defined in the ANVS-AI Master Plan.

---

## 1. Master Plan Execution Matrix Overview

| PR ID | Workstream / Domain | Current Repo State | Critical Target Requirements |
| :--- | :--- | :--- | :--- |
| **PR-01** | Baseline Hygiene & Workspace Standardization | Duplicate dirs, tracked SQLite db, divergent schemas | Untrack db, standardize on underscore directories, add deep `/healthz` & `/readyz`, ensure clean CI |
| **PR-02** | Authentication, Sessions & Tenant Context | Fake `/auth/token` trusts request body, no DB auth | Bcrypt password verification, DB-backed user/org lookup, user sessions, ticket security |
| **PR-03** | Data Plane Completion & Row Level Security | 6 tables in Alembic, missing 8 enterprise tables | 14 tables, full RLS enforcement, outbox pattern, seed data, database session cleanup |
| **PR-04** | Real-time Gateway & WebSocket Protocol | In-memory connection map, no frame rate limits | Ticket validation, Redis Pub/Sub backplane, client heartbeat, state synchronization |
| **PR-05** | LiveKit SFU Integration & Media Plane | Mock `create_room`/`delete_room`, fake tokens | Real LiveKit Twirp client, room management, webhook verification, participant auth |
| **PR-06** | Audio Ingress, Ingestion & Watermark Drop | `AudioIngestionPipeline` disconnected from SFU | LiveKit audio track subscription, 20ms framing, 48kHz->16kHz resampling, 20kHz echo filter |
| **PR-07** | STT Speech Recognition Worker Fleet | Faster-Whisper with mock fallback, disconnected | Streaming audio processing, partial/final events, ISO 639-3 enforcement, Lineage Invariant #2 |
| **PR-08** | Speaker Diarization & Voice Embeddings | PyAnnote fallback to mock, no persistence | PyAnnote 3.1 streaming diarization, speaker voice embeddings, speaker turns |
| **PR-09** | Neural Machine Translation (NMT) Fleet | NLLB-200 with mock fallback, fanout logic | Multi-language fanout from source segment (Invariant #2), batch inference, language validation |
| **PR-10** | TTS Synthesis & Ultrasonic Watermarking | Piper/Bark fallback, watermark injection works | Real speech synthesis, 20kHz ultrasonic pilot tone (Invariant #3), LiveKit audio track egress |
| **PR-11** | Voice Cloning & Preservation Worker | `services/voice-worker` is 48-byte empty stub | Real `voice_worker`, voice profile extraction, zero-shot voice cloning with consent check |
| **PR-12** | AI In-Meeting Copilot & RAG Assistant | Mock assistant with regex action items | pgvector semantic similarity search, transcript citation provenance, LLM streaming |
| **PR-13** | Pipeline Orchestration, DLQ & Resilience | Redis Streams bus, 3-retry DLQ exists | Auto-stream trimming (`XTRIM`), poison pill quarantine (Invariant #4), failover monitor |
| **PR-14** | Frontend Meeting Web App & Admin Portal | Hardcoded `fake_lk_token` and mock admin token | Real API auth, LiveKit SFU video/audio connection, real-time captions, role enforcement |
| **PR-15** | Production Hardening, Verification & GA | Placeholder test dirs, premature release doc | Realtime/security/integration tests, Helm/Terraform verification, true release certification |

---

## 2. Granular PR Implementation Specifications

### PR-01: Baseline Hygiene & Workspace Standardization
- **Current Repository State**:
  - `ai-content-agent.db` committed in root directory.
  - Hyphenated duplicate directories exist:
    - `services/assistant-worker` vs `services/assistant_worker`
    - `services/realtime-gateway` vs `services/realtime_gateway`
    - `services/speaker-worker` vs `services/speaker_worker`
    - `services/stt-worker` vs `services/stt_worker`
    - `services/translation-worker` vs `services/translation_worker`
    - `services/tts-worker` vs `services/tts_worker`
    - `packages/event-schema` vs `packages/event_schema`
    - `packages/language-registry` vs `packages/language_registry`
  - `/health` endpoint only does basic status check; no deep `/healthz` (liveness) or `/readyz` (readiness) verifying DB and Redis connectivity.
- **Affected Files**:
  - `ai-content-agent.db` (REMOVE)
  - `.gitignore` (MODIFY)
  - Hyphenated directories (REMOVE)
  - `services/api/routers/health.py` (MODIFY/EXPAND)
  - `pyproject.toml` & `package.json` (VERIFY)
- **Target Deliverable**: Clean workspace, canonical underscore package paths, deep health checks, zero lint/format errors.

---

### PR-02: Authentication, Sessions & Tenant Context
- **Current Repository State**:
  - `services/api/routers/auth.py` accepts client `tenant_id` and `role` without DB lookup.
  - No user registration, password hashing verification, or session invalidation.
- **Affected Files**:
  - `services/api/routers/auth.py` (REFACTOR)
  - `packages/auth/tokens.py` (UPDATE)
  - `packages/auth/passwords.py` (NEW / VERIFY)
  - `packages/auth/middleware.py` (UPDATE)
  - `tests/unit/test_auth_tokens.py` (UPDATE)
- **Target Deliverable**: Cryptographically secure authentication, bcrypt password hashing, user sessions, secure tickets with expiration, strict tenant extraction from authenticated user context.

---

### PR-03: Data Plane Completion & Row Level Security
- **Current Repository State**:
  - Alembic migration `0001_initial_schema_and_rls.py` defines only 6 tables (`organizations`, `users`, `meetings`, `participants`, `transcript_segments`, `transcript_embeddings`).
  - Missing 8 critical tables:
    - `user_sessions`
    - `organization_members`
    - `meeting_settings`
    - `source_segments`
    - `voice_profiles`
    - `meeting_chat`
    - `outbox_events`
    - `idempotency_keys`
- **Affected Files**:
  - `migrations/versions/0002_complete_enterprise_schema.py` (NEW)
  - `packages/database/models/` (EXPAND with new SQLAlchemy 2.0 models)
  - `packages/database/session.py` (RLS session context manager)
  - `packages/database/seed.py` (EXPAND)
  - `tests/unit/test_database_models.py` (EXPAND)
- **Target Deliverable**: 14 enterprise PostgreSQL tables with RLS enabled and forced on all tenant tables; transactional outbox pattern support.

---

### PR-04: Real-time Gateway & WebSocket Protocol
- **Current Repository State**:
  - `services/realtime_gateway/server.py` and `manager.py` handle WebSocket frames in-memory.
  - Ticket validation exists but lacks integration with PR-02 session revocation and rate limiting.
- **Affected Files**:
  - `services/realtime_gateway/server.py` (UPDATE)
  - `services/realtime_gateway/manager.py` (UPDATE)
  - `services/realtime_gateway/subscriber.py` (UPDATE)
  - `tests/unit/test_websocket_gateway.py` (EXPAND)
  - `tests/contract/test_websocket_gateway_contracts.py` (VERIFY)
- **Target Deliverable**: Robust WebSocket gateway supporting multi-node scale, frame validation, client heartbeats (ping/pong), connection admission control.

---

### PR-05: LiveKit SFU Integration & Media Plane
- **Current Repository State**:
  - `services/api/services/livekit_service.py` has mock `create_room` and `delete_room`.
  - Webhooks lack full callback dispatching to meeting state machines.
- **Affected Files**:
  - `services/api/services/livekit_service.py` (REFACTOR with livekit-api client)
  - `services/api/routers/rooms.py` (UPDATE)
  - `tests/unit/test_livekit_service.py` (UPDATE)
  - `tests/unit/test_livekit_webhooks.py` (UPDATE)
- **Target Deliverable**: Real LiveKit RoomService twirp client integration for room creation, participant listing, track subscription grants, and secure webhook verification.

---

### PR-06: Audio Ingress, Ingestion & Watermark Drop
- **Current Repository State**:
  - `packages/audio/ingestion.py` implements `AudioIngestionPipeline`, but no runtime service connects LiveKit audio tracks to it.
- **Affected Files**:
  - `services/audio_ingress/` (NEW worker or daemon)
  - `packages/audio/ingestion.py` (REFINE)
  - `packages/audio/watermark.py` (VERIFY 20kHz FFT detection)
  - `tests/unit/test_audio_ingestion.py` (EXPAND)
- **Target Deliverable**: Participant WebRTC audio ingestion from LiveKit SFU, 48kHz to 16kHz resampling, 20ms chunking, ultrasonic 20kHz watermark detection, dropping watermarked frames (Invariant #3).

---

### PR-07: Speech-to-Text (STT) Worker Fleet
- **Current Repository State**:
  - `services/stt_worker/` implements Faster-Whisper engine and Redis stream consumer.
  - Has mock fallback.
- **Affected Files**:
  - `services/stt_worker/engine.py` (REFINE)
  - `services/stt_worker/consumer.py` (REFINE)
  - `tests/unit/test_stt_worker.py` (EXPAND)
  - `tests/contract/test_stt_contracts.py` (VERIFY)
- **Target Deliverable**: Robust streaming transcription, partial/final segment emission, strict ISO 639-3 normalization, propagation of immutable `source_segment_id` (Invariant #2).

---

### PR-08: Diarization & Speaker Worker
- **Current Repository State**:
  - `services/speaker_worker/` has PyAnnote integration with mock fallback.
  - Speaker turns are emitted but not linked to persistent speaker profiles.
- **Affected Files**:
  - `services/speaker_worker/engine.py` (UPDATE)
  - `services/speaker_worker/consumer.py` (UPDATE)
  - `tests/unit/test_speaker_worker.py` (EXPAND)
- **Target Deliverable**: Accurate speaker diarization, voice embedding extraction, speaker profile matching, speaker attribution in transcript events.

---

### PR-09: Neural Machine Translation (NMT) Fleet
- **Current Repository State**:
  - `services/translation_worker/` supports Meta NLLB-200 with mock fallback.
  - Translates `original_text` to active participant target languages.
- **Affected Files**:
  - `services/translation_worker/engine.py` (UPDATE)
  - `services/translation_worker/consumer.py` (UPDATE)
  - `tests/unit/test_translation_worker.py` (EXPAND)
- **Target Deliverable**: High-throughput multi-lingual translation fanout, caching of common translations, sub-250ms latency, lineage preservation (Invariant #2).

---

### PR-10: TTS Synthesis & Ultrasonic Watermarking
- **Current Repository State**:
  - `services/tts_worker/` supports Piper/Bark and embeds 20 kHz pilot tone.
  - Synthetic audio is pushed to Redis, but never delivered to LiveKit egress.
- **Affected Files**:
  - `services/tts_worker/engine.py` (UPDATE)
  - `services/tts_worker/consumer.py` (UPDATE)
  - `services/tts_worker/egress.py` (NEW - LiveKit audio track publishing)
  - `tests/unit/test_tts_worker.py` (EXPAND)
- **Target Deliverable**: High-quality multilingual speech synthesis, mandatory 20 kHz ultrasonic watermark embedding (Invariant #3), real-time audio playback into recipient LiveKit audio tracks.

---

### PR-11: Voice Cloning & Preservation Worker
- **Current Repository State**:
  - `services/voice-worker` is a 48-byte empty stub.
- **Affected Files**:
  - `services/voice_worker/` (NEW full implementation)
    - `__init__.py`
    - `main.py`
    - `engine.py` (voice profiling and zero-shot cloning)
    - `consumer.py` (Redis Streams listener)
    - `types.py`
  - `tests/unit/test_voice_worker.py` (NEW)
- **Target Deliverable**: Speaker voice profiling, consent verification, zero-shot/few-shot voice preservation for translated TTS synthesis.

---

### PR-12: AI In-Meeting Copilot & RAG Assistant Worker
- **Current Repository State**:
  - `services/assistant_worker/` uses regex matching for action items with mock LLM fallback.
- **Affected Files**:
  - `services/assistant_worker/engine.py` (REFACTOR with RAG & pgvector)
  - `services/assistant_worker/consumer.py` (UPDATE)
  - `tests/unit/test_assistant_worker.py` (EXPAND)
- **Target Deliverable**: Retrieval-Augmented Generation (RAG) over in-meeting transcripts via PostgreSQL pgvector, strict citation provenance with timestamps and speaker attribution.

---

### PR-13: Pipeline Orchestration, DLQ & Resilience
- **Current Repository State**:
  - `services/orchestrator/` manages stream topology and worker heartbeats.
  - Lacks auto-trimming and full consumer recovery.
- **Affected Files**:
  - `services/orchestrator/pipeline.py` (UPDATE)
  - `services/orchestrator/dlq.py` (UPDATE - Invariant #4 quarantine)
  - `services/orchestrator/monitor.py` (UPDATE)
  - `tests/unit/test_orchestrator.py` (EXPAND)
  - `tests/chaos/test_pipeline_chaos_resilience.py` (EXPAND)
- **Target Deliverable**: Resilient Redis Streams orchestration, exponential backoff, terminal DLQ quarantine after 3 failures (Invariant #4), auto-healing worker pool.

---

### PR-14: Frontend Meeting Web App & Admin Portal
- **Current Repository State**:
  - Frontends generate fake tokens and mock credentials.
- **Affected Files**:
  - `apps/web/src/app/page.tsx` (UPDATE - real API calls)
  - `apps/web/src/app/meeting/[id]/page.tsx` (UPDATE - real LiveKit room connection)
  - `apps/web/src/lib/api.ts` (NEW / EXPAND)
  - `apps/admin/src/context/AdminAuthContext.tsx` (UPDATE - real admin auth)
- **Target Deliverable**: Production-grade frontend applications connected to real API endpoints, real LiveKit SFU video/audio rendering, live multilingual captions overlay, and responsive AI Copilot panel.

---

### PR-15: Production Hardening, Verification & GA
- **Current Repository State**:
  - `tests/realtime`, `tests/security`, and `tests/integration` are empty stubs (`.gitkeep`).
  - `RELEASE_CERTIFICATION.md` contains unverified claims.
- **Affected Files**:
  - `tests/realtime/` (NEW comprehensive test suite)
  - `tests/security/` (NEW security penetration & RLS leak tests)
  - `tests/integration/` (NEW end-to-end integration tests)
  - `RELEASE_CERTIFICATION.md` (UPDATE with genuine empirical benchmarks)
- **Target Deliverable**: Full test suite passing with 0 errors and 0 warnings, verified container builds, Helm/Terraform validation, genuine Release Certification.
