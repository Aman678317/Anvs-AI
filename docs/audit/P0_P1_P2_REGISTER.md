# ANVS-AI Multilingual Meeting Platform — Defect Register (Phase 0)

> **Document**: `docs/audit/P0_P1_P2_REGISTER.md`  
> **Author**: Lead Principal Software Engineer & Security Team  
> **Date**: September 22, 2026  
> **Status**: Comprehensive Severity-Ranked Defect Catalog

---

## 1. Defect Severity Classification

- **P0 (Blocker)**: Critical security vulnerabilities, architectural disconnects, missing core workers, hardcoded fake credentials, or broken invariants that prevent production operation.
- **P1 (Critical)**: Unhandled runtime errors, rate limiting edge cases, incomplete test coverage, or unpersisted state leading to failure under load.
- **P2 (Major)**: Missing deep liveness/readiness probes, styling/formatting discrepancies, or operational maintenance gaps.

---

## 2. P0 Blockers Register

| ID | Location | Observed Behavior | Expected Behavior | Architectural / Security Risk | Target PR | Test Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P0-01** | `services/api/routers/auth.py:40-57` | `/auth/token` mints JWTs using client-supplied `tenant_id`, `user_id`, and `role` without password validation or DB query. | Must authenticate user email and password against PostgreSQL `users` table, derive `tenant_id` and `role` securely from DB record. | **Catastrophic Privilege Escalation**: Any user can grant themselves `ADMIN` role on any tenant organization. | **PR-02** | `tests/unit/test_auth_tokens.py`, security penetration tests |
| **P0-02** | `apps/web/src/app/page.tsx:98, 128`<br>`apps/web/src/app/meeting/[id]/page.tsx:53` | Generates client-side `fake_lk_token_${id}` and `ticket_${id}` strings. | Client must call backend `/api/v1/rooms/join` to obtain server-signed JWT and session ticket. | **Media Plane Failure**: WebRTC connections fail immediately when connecting to authentic LiveKit SFU instances. | **PR-05** / **PR-14** | `tests/e2e/test_multiuser_meeting_lifecycle.py` |
| **P0-03** | `apps/admin/src/context/AdminAuthContext.tsx:45, 53` | Hardcodes `token: "mock_admin_bearer_token"`. | Admin portal must authenticate with backend API and store genuine JWT bearer token. | **Admin Security Bypass**: Client-side admin state without token verification. | **PR-02** / **PR-14** | `tests/contract/test_admin_contracts.py` |
| **P0-04** | `services/api/services/livekit_service.py:79-98` | `create_room` and `delete_room` are local stubs returning mock dictionaries with dummy UUIDs. | Must invoke LiveKit `RoomServiceClient` (Twirp protocol) to provision and terminate rooms on SFU. | **Orphaned Media Sessions**: Real SFU rooms are never provisioned or cleaned up on the server. | **PR-05** | `tests/unit/test_livekit_service.py` with LiveKit API mock |
| **P0-05** | `packages/audio/ingestion.py`<br>`services/tts_worker/` | `AudioIngestionPipeline` is never connected to LiveKit SFU audio egress; TTS worker never publishes back to LiveKit audio tracks. | Participant audio from LiveKit SFU must be ingested into `AudioIngestionPipeline`; synthetic audio must be published into LiveKit audio tracks. | **Media Disconnect**: No speech is ever transcribed from live calls, and translated speech is never heard by participants. | **PR-05** / **PR-06** / **PR-10** | End-to-end audio loopback verification tests |
| **P0-06** | `services/voice-worker/` | Directory contains only a 48-byte `__init__.py`. No implementation exists. | Full `voice_worker` implementation extracting speaker voice embeddings and cloning speech for TTS. | **Missing Feature**: Voice preservation/cloning advertised in architecture is nonexistent. | **PR-11** | `tests/unit/test_voice_worker.py` |
| **P0-07** | `migrations/versions/0001_initial_schema_and_rls.py` | Only 6 tables exist in Alembic schema. Missing 8 enterprise tables. | Schema must contain 14 tables: `organizations`, `users`, `meetings`, `participants`, `transcript_segments`, `transcript_embeddings`, `user_sessions`, `organization_members`, `meeting_settings`, `source_segments`, `voice_profiles`, `meeting_chat`, `outbox_events`, `idempotency_keys`. | **Data Loss & Invariant Failure**: Lack of `source_segments` violates immutable source lineage (Invariant #2); lack of `user_sessions` prevents token revocation. | **PR-03** | `tests/unit/test_database_models.py`, Alembic migration upgrade tests |
| **P0-08** | `services/` & `packages/` | Duplicate hyphenated and underscored directories exist (`stt-worker` vs `stt_worker`, etc.). | Canonical directories must use Python-standard underscore naming (`stt_worker`, `event_schema`, etc.). | **Build Drift & Import Confusion**: Parallel directories risk divergent codebases and package resolution bugs. | **PR-01** | Repository file integrity audit |
| **P0-09** | Root directory | `ai-content-agent.db` (77.8 KB SQLite file) is tracked in Git. | Database files must be untracked and excluded via `.gitignore`. | **Repo Bloat & Accidental Data Leak**: SQLite database tracked in version control. | **PR-01** | Git status cleanliness check |
| **P0-10** | `RELEASE_CERTIFICATION.md` | Claims 100% GA production readiness with empty test suites and mock tokens. | Certification document must reflect empirical reality backed by passing integration and load tests. | **Integrity & Compliance Failure**: False production claims undermine enterprise release readiness. | **PR-15** | Benchmark validation suite |

---

## 3. P1 Critical Defects Register

| ID | Location | Observed Behavior | Expected Behavior | Target PR | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P1-01** | `services/api/routers/rooms.py:70, 200` | Unawaited async mock warning: `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`. | All async operations in room router and test fixtures must be properly awaited. | **PR-01** / **PR-05** | Pytest run with `-W error::RuntimeWarning` |
| **P1-02** | `services/api/routers/rooms.py:135-150` | Join room passcode verification hits rate limiter 429 in rapid test execution. | Rate limiter must support test-mode bypass or reset mechanism during unit test fixtures. | **PR-01** / **PR-04** | `tests/unit/test_room_manager.py` |
| **P1-03** | `tests/realtime/`, `tests/security/`, `tests/integration/` | Directories contain only `.gitkeep` files. | Comprehensive automated tests must be implemented for WebSocket protocol, security RLS penetration, and integration flows. | **PR-15** | Full test execution |
| **P1-04** | `apps/meeting-client/src/index.ts` | 40-line stub with no functional logic. | Complete isomorphic client SDK with reconnection, token refresh, and signaling. | **PR-14** | TypeScript compilation & client tests |
| **P1-05** | `services/realtime_gateway/manager.py` | Connection state held purely in local process memory. | Connection presence backed by Redis keys to allow multi-instance gateway scaling. | **PR-04** | Gateway concurrency tests |
| **P1-06** | `services/orchestrator/pipeline.py` | Streams created without explicit `MAXLEN` or `XTRIM` policy. | Stream trimming policy enforced to cap Redis memory growth on long meetings. | **PR-13** | Redis memory leak chaos tests |
| **P1-07** | `services/assistant_worker/engine.py:59` | Action items extracted using regex patterns `r"\b(will\|shall\|todo\|action item...)\b"`. | Semantic extraction using LLM structured output and pgvector citation embeddings. | **PR-12** | `tests/unit/test_assistant_worker.py` |

---

## 4. P2 Major Defects Register

| ID | Location | Observed Behavior | Expected Behavior | Target PR | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P2-01** | `services/api/routers/health.py` | Basic 200 OK without verifying database and Redis readiness. | `/healthz` for liveness; `/readyz` performing `SELECT 1` on DB and `PING` on Redis. | **PR-01** | Unit tests for health endpoints |
| **P2-02** | `packages/database/models/` | No transactional outbox table or polling worker. | Outbox pattern ensures guaranteed Redis stream event emission upon database transaction commit. | **PR-03** | Database transaction tests |
| **P2-03** | `packages/language_registry/languages.py` | Strictly accepts ISO 639-3; rejects standard 2-letter ISO 639-1 without alias mapping. | Automatic transparent aliasing from 2-letter codes (`en` -> `eng`, `hi` -> `hin`). | **PR-01** | Language registry unit tests |
| **P2-04** | CI & Formatting | Prettier fails on Helm templates unless explicitly ignored in `.prettierignore`. | `.prettierignore` properly configured to ignore Helm YAML template tags. | **PR-01** | `pnpm run format:check` |
