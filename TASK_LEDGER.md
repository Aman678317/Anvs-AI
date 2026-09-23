# ANVS-AI Multilingual Meeting Platform — Task Ledger (PR-00 through PR-15)

> **Document Version**: 4.0.0  
> **Master Sequence**: Aligned with Section 24 of the Master Execution Prompt v4.0  
> **Status Lifecycle**: `COMPLETE`, `IN_PROGRESS`, `PENDING`, `BLOCKED`

---

## PR Summary & Gate Status Overview

| PR | Scope | Gate Target | Status |
|---|---|---|---|
| **PR-00** | Re-baseline & Audit | Tag current state; reconcile stale audits; establish evidence ledger; no blind changes | **COMPLETE (Stage 0)** |
| **PR-01** | Repo / Config / CI | Canonical structure; env validation; health/readiness; CI/security/build gates | **COMPLETE (Passes CI)** |
| **PR-02** | Auth / Sessions | Real identity; login/register; session revoke/logout; no spoofable tenant/role | **COMPLETE** |
| **PR-03** | Org / RBAC | Membership; roles; invitations; host/co-host/participant controls | **COMPLETE** |
| **PR-04** | DB / RLS | Master 14-table schema; migrations; FORCE RLS; negative tests | **COMPLETE** |
| **PR-05** | Meetings Lifecycle | Create/join/end; participant preferences; waiting room; lifecycle reconciliation | **COMPLETE** |
| **PR-06** | Contracts & Envelopes | Canonical v1.2 event envelope (lineage, hops, causation); JSON Schema / golden fixtures | **COMPLETE** |
| **PR-07** | Event Bus & Streams | Redis Streams; consumer groups; outbox; dedup; retry budget; DLQ | **COMPLETE** |
| **PR-08** | Realtime State & Resync | Dynamic state versioning (monotonic); snapshots; gap recovery; reconnect continuity | **COMPLETE** |
| **PR-09** | Real LiveKit Media Plane | Real room operations; no synthetic active room fallback; browser join; webhooks | **PENDING** |
| **PR-10** | Source Audio & STT Ingest | Real LiveKit audio subscriber; human track gate; VAD; streaming STT; immutable source | **PENDING** |
| **PR-11** | Real Translation Fan-out | Provider-neutral capability registry; per-listener target resolution; glossary context | **PENDING** |
| **PR-12** | TTS & LiveKit Audio Egress | Real LiveKit AudioSource track publication; audience scoping; deterministic timing/drop | **PENDING** |
| **PR-13** | Resilience & Chaos | Stale-drop; reconnect; dedup; backpressure; failure injection; meeting continuity | **COMPLETE (Unit/Chaos)** |
| **PR-14** | Conversation & Admin | Multilingual chat; captions/transcripts; assistant Q&A; memory orchestration | **IN_PROGRESS** |
| **PR-15** | GA Release Certification | Browser/media E2E; language benchmark matrix; security audit; rollback verification | **PENDING** |

---

## Detailed PR Task Breakdown

### PR-00: Repository Re-baseline & Audit
- **Goal**: Establish empirical ground truth, inventory existing tree, reconcile historical findings without blind rewrites.
- **Tasks**:
  - [x] STEP-00-1: Create `CURRENT_STATE.md` recording monorepo inventory, branch, commit, and component statuses.
  - [x] STEP-00-2: Reconcile historical findings from `docs/audit/REPOSITORY_AUDIT.md` (label FIXED, STILL OPEN, STALE).
  - [x] STEP-00-3: Create `TASK_LEDGER.md`, `IMPLEMENTATION_MAP.md`, `OPEN_DECISIONS.md`, `EVIDENCE_LEDGER.md`, and `RELEASE_STATUS.md`.
- **Gate**: Zero business logic changes; audit documents committed; baseline verified.

### PR-01: Repository, Configuration & CI Hygiene
- **Goal**: Canonicalize package directories, ensure toolchain consistency, fail fast on invalid production configs.
- **Tasks**:
  - [x] STEP-01-1: Gitignore legacy hyphenated duplicate directories (`services/*-worker`, `packages/event-schema`).
  - [x] STEP-01-2: Create top-level `app/` entrypoint alias resolving uvicorn import confusion.
  - [x] STEP-01-3: Verify Ruff linting (`ruff check .`) and Prettier formatting (`pnpm run format:check`).
  - [x] STEP-01-4: Update `packages/config/settings.py` to prohibit default mock engines when `APP_ENV=production`.
- **Gate**: CI workflow passes `ruff check .`, `pnpm run format:check`, and `pnpm run typecheck`. (PR-01 COMPLETE)

### PR-02: Authentication, Identity & Sessions
- **Goal**: Authoritative identity verification, bcrypt password hashing, scoped session tokens, no spoofable roles.
- **Tasks**:
  - [x] STEP-02-1: Implement `/api/v1/auth/register` with bcrypt password hashing and tenant provisioning.
  - [x] STEP-02-2: Implement `/api/v1/auth/login` returning signed JWT access tokens with server-verified role.
  - [x] STEP-02-3: Enforce `/api/v1/auth/token` database derivation of tenant and role.
  - [x] STEP-02-4: Implement signed dual-token session tickets (`/api/v1/auth/ticket`) with 300s TTL.
- **Gate**: Cross-tenant spoofing impossible; unauthenticated access denied; test suite passing.

### PR-03: Organization, Membership & RBAC
- **Goal**: Multi-tenant organization scoping, membership roles, and permission gates.
- **Tasks**:
  - [x] STEP-03-1: Implement `Organization` and `OrganizationMember` models and relationship constraints.
  - [x] STEP-03-2: Create RBAC permission hierarchy (`Permission.MEETING_CREATE`, `Permission.PARTICIPANT_EVICT`, etc.).
  - [x] STEP-03-3: Enforce `require_permission` route dependencies on administrative endpoints.
- **Gate**: RBAC privilege escalation tests passing.

### PR-04: Database Schema, Migrations & PostgreSQL 16 RLS
- **Goal**: Master 14-table schema with PostgreSQL Row Level Security (RLS) enforcement.
- **Tasks**:
  - [x] STEP-04-1: Implement Alembic migration `0002_complete_enterprise_schema.py` covering all 14 tables.
  - [x] STEP-04-2: Configure PostgreSQL RLS policies with `SET LOCAL app.current_tenant_id = :tenant_id`.
  - [x] STEP-04-3: Add `pgvector` HNSW indexes for 1536-dim semantic embeddings and 512-dim voice profiles.
  - [x] STEP-04-4: Validate transactional session manager in `packages/database/session.py`.
- **Gate**: Negative multi-tenant isolation tests pass with zero data leakage across tenant boundaries.

### PR-05: Meeting Lifecycle & Participant Coordination
- **Goal**: End-to-end meeting creation, admission control, participant state management, and host termination.
- **Tasks**:
  - [x] STEP-05-1: REST endpoints `/api/v1/rooms/create`, `/api/v1/rooms/{id}`, `/api/v1/rooms/{id}/join`, `/api/v1/rooms/{id}/end`.
  - [x] STEP-05-2: Passcode verification, waiting room state transition, and participant roster tracking.
  - [x] STEP-05-3: Graceful room termination disconnecting active WebSockets and LiveKit rooms.
- **Gate**: Room lifecycle state machine transitions verified.

### PR-06: Event Contracts & Canonical Envelope Lineage
- **Goal**: Reconcile `BaseEvent` with v1.2 specification including full causal lineage, hop limits, and TTL.
- **Tasks**:
  - [x] STEP-06-1: Upgrade `BaseEvent` in `packages/event_schema/events.py` with `event_version`, `correlation_id`, `causation_id`, `parent_event_id`, `sequence_number`, `hop_count`, `max_hops`, `ttl_seconds`, and `occurred_at`.
  - [x] STEP-06-2: Align TypeScript contract types in `packages/contracts/src/events.ts`.
  - [x] STEP-06-3: Add lineage verification tests validating causal parent-child tracking from `SourceSegmentEvent`.
- **Gate**: Cross-language contract serialization parity proven via golden schema tests. (PR-06 COMPLETE)

### PR-07: Redis Streams Event Bus & DLQ Backpressure
- **Goal**: Distributed stream bus coordination, consumer groups, idempotency, and poison-pill DLQ quarantine.
- **Tasks**:
  - [x] STEP-07-1: Redis consumer group registration for all worker services.
  - [x] STEP-07-2: `DLQRetryManager` with exponential backoff (max 3 retries) and dead-letter routing.
  - [x] STEP-07-3: Implement automatic stream trimming (`XTRIM`) to bound memory growth during long meetings.
- **Gate**: Invariant #4 verified: failed events quarantined to DLQ without crashing the pipeline.

### PR-08: Realtime State, Versioning & Reconnect Continuity
- **Goal**: Replace static `state_version=1` with monotonically evolving state, snapshot resync, and gap recovery.
- **Tasks**:
  - [x] STEP-08-1: Add monotonic state version counter to `ConnectionManager` per meeting room.
  - [x] STEP-08-2: Implement `WSClientResyncFrame` and `WSServerResyncResponseFrame` for gap reconciliation.
  - [x] STEP-08-3: Support snapshot and missed frames recovery in `ConnectionManager` and `server.py`.
- **Gate**: Simulated network disconnect recovers chat and participant state without data loss. (PR-08 COMPLETE)

### PR-09: LiveKit Real Media Plane Integration
- **Goal**: Real LiveKit Room Service operations, surface true failures in production, authentic WebRTC tokens.
- **Tasks**:
  - [x] STEP-09-1: Remove synthetic active room fallback in `LiveKitService.create_room` during non-dev environments.
  - [ ] STEP-09-2: Real LiveKit Twirp API room creation, participant listing, and room deletion.
  - [ ] STEP-09-3: Implement webhook receiver with HMAC signature verification and room state synchronization.
- **Gate**: Real LiveKit room creation succeeds against LiveKit server; failures surfaced explicitly.

### PR-10: Human Audio Ingest, Source Gate & STT Fleet
- **Goal**: Connect live WebRTC audio track to `AudioIngressService`, enforce human source gate, streaming STT.
- **Tasks**:
  - [ ] STEP-10-1: Create LiveKit audio subscription worker connecting active participant microphone tracks to `AudioIngressService`.
  - [ ] STEP-10-2: Verify 20ms framing, 20kHz acoustic watermark loop rejection (Invariant #3), and VAD.
  - [ ] STEP-10-3: Faster-Whisper streaming STT generating immutable `SourceSegmentEvent` with language detection.
- **Gate**: Human speech transcribed and published to `STREAM_TRANSCRIPTS`; synthetic audio dropped.

### PR-11: Translation Worker & Concurrent Fan-Out
- **Goal**: Extensible language capability registry, per-listener target language resolution, concurrent fan-out.
- **Tasks**:
  - [ ] STEP-11-1: Upgrade `packages/language_registry` with capability metadata (checkpoints, licensing, tiers).
  - [ ] STEP-11-2: Implement listener-specific language routing: single source segment $S$ fans out to $T_{en}, T_{mr}, T_{ja}$ concurrently.
  - [ ] STEP-11-3: Context injection: supply recent stable source segments and glossary hints to NMT engine.
- **Gate**: Invariant #2 verified: all translations derive strictly from `source_segment_id`.

### PR-12: Real TTS Synthesis, LiveKit Audio Egress & Timing
- **Goal**: Real LiveKit audio track publication via `AudioSource`, audience scoping, deterministic stale-drop.
- **Tasks**:
  - [ ] STEP-12-1: Implement real LiveKit backend track publisher using `livekit.rtc.AudioSource` and `LocalAudioTrack`.
  - [ ] STEP-12-2: Audience-scoped track routing: English listeners subscribe to EN track; Marathi listeners subscribe to MR track.
  - [ ] STEP-12-3: Timing engine: drop stale translated audio if backlog exceeds threshold (e.g. >2.5s late).
- **Gate**: Real synthesized watermarked audio published to LiveKit SFU and audible to listener.

### PR-13: Resilience, Chaos & Meeting Continuity
- **Goal**: Verify platform survivability during STT, NMT, TTS, Redis, and network outages.
- **Tasks**:
  - [x] STEP-13-1: Test pipeline chaos resilience under simulated worker crashes (`tests/chaos`).
  - [x] STEP-13-2: Fallback to original human audio when AI translation workers fail.
  - [x] STEP-13-3: Load concurrency benchmarking under multi-participant stress (`tests/load`).
- **Gate**: Meeting remains connected and usable when AI workers are terminated.

### PR-14: Multilingual Chat, Captions & Grounded Assistant
- **Goal**: Persistent chat with separate original/translated text, live captions, grounded copilot RAG.
- **Tasks**:
  - [x] STEP-14-1: Multilingual chat protocol preserving original message alongside target translations.
  - [x] STEP-14-2: Visual distinction between partial/draft captions and finalized transcript segments.
  - [ ] STEP-14-3: Assistant memory integration: working memory meeting window, episodic memory, tenant scoping.
- **Gate**: Chat history recovered after reconnect; assistant answers grounded strictly in meeting context.

### PR-15: Production Hardening & GA Release Certification
- **Goal**: End-to-end multi-browser vertical slice verification, security audit, and evidence release package.
- **Tasks**:
  - [x] STEP-15-1: End-to-end multi-service platform integration suite (`tests/integration`).
  - [x] STEP-15-2: OWASP security headers, secret sanitization, and crypto audit (`tests/security`).
  - [ ] STEP-15-3: Real multi-browser WebRTC vertical slices (Slice A through Slice E).
  - [ ] STEP-15-4: Comprehensive GA Release Certification report backed by empirical runtime traces.
- **Gate**: Slices A–E pass with real audio; no mocks in production path; evidence package complete.
