# ANVS-AI Multilingual Meeting Platform — Evidence Ledger (Stage 0)

> **Document Version**: 4.0.0  
> **Evaluation Date**: September 24, 2026  
> **Commit SHA**: `abfed21f88b774347dcd586b469d786ccad36119`  
> **Active Branch**: `feat/pr-01-baseline-hygiene`  
> **Guiding Principle**: Never fabricate test output. Never confuse mock test passage with real-media runtime proof.

---

## 1. Test Suite & Verification Baseline

| Test Category          | Directory Path       | Test Files                                  | Total Test Cases | Execution Status | Evidence Type                      |
| ---------------------- | -------------------- | ------------------------------------------- | ---------------- | ---------------- | ---------------------------------- |
| **Unit Tests**         | `tests/unit/`        | 31 test files                               | ~245 tests       | **PASSING**      | Synthetic / Mock engine units      |
| **Contract Tests**     | `tests/contract/`    | 15 test files                               | ~60 tests        | **PASSING**      | Pydantic schema serialization      |
| **Security Audit**     | `tests/security/`    | `test_security_audit.py`                    | 12 tests         | **PASSING**      | Invariants 1–4, RBAC, RLS, Headers |
| **Integration**        | `tests/integration/` | `test_platform_integration.py`              | 6 tests          | **PASSING**      | Multi-service orchestration mocks  |
| **Chaos & Resilience** | `tests/chaos/`       | `test_pipeline_chaos_resilience.py`         | 4 tests          | **PASSING**      | Worker crash and DLQ recovery      |
| **Load Concurrency**   | `tests/load/`        | `test_load_concurrency.py`, `locustfile.py` | 2 tests          | **PASSING**      | Synthetic token/room load          |
| **Realtime WebSocket** | `tests/realtime/`    | `.gitkeep` (empty)                          | 0 tests          | **UNVERIFIED**   | Missing automated suite            |
| **Real LiveKit Media** | `tests/e2e/`         | `test_meeting_e2e.py`                       | 3 tests          | **MOCKED**       | Mock SFU connection only           |

---

## 2. Code Quality & Toolchain Verification

| Check                    | Tool / Engine       | Command                  | Status      | Notes                                           |
| ------------------------ | ------------------- | ------------------------ | ----------- | ----------------------------------------------- |
| **Python Syntax**        | Python `compileall` | `python -m compileall .` | **PASSING** | 0 syntax errors across 316 files                |
| **Python Linting**       | Ruff v0.6.9         | `ruff check .`           | **PASSING** | Clean imports (I001), 0 unused variables (F841) |
| **TypeScript Typecheck** | TypeScript 5.4.5    | `pnpm exec tsc --noEmit` | **PASSING** | Strict null checks & mutable refs passing       |
| **Prettier Formatting**  | Prettier v3.2.5     | `pnpm run format:check`  | **PASSING** | 100 print width, 2-space tab, double quotes     |
| **Database Migrations**  | Alembic             | `alembic check`          | **PASSING** | Migrations 0001 and 0002 valid                  |

---

## 3. Real Media vs. Mock Proof Boundaries

The following matrix distinguishes between what is empirically proven through native runtime execution vs. what remains simulated or mocked:

| Feature / Pathway       | Mock / Synthetic Proof                    | Real Runtime Proof                 | Gap to Production Truth                              |
| ----------------------- | ----------------------------------------- | ---------------------------------- | ---------------------------------------------------- |
| **Room Creation**       | Tested with synthetic `RM_...` dictionary | LiveKit Twirp API call             | Need LiveKit server reachable via `LIVEKIT_URL`      |
| **Audio Ingress**       | Unit tested with numpy sine waves         | Browser microphone via WebRTC      | Need LiveKit audio track subscription worker         |
| **Watermark Loop Drop** | Unit tested with 20kHz FFT detection      | Real speaker loop playback         | Proven mathematically; needs live audio confirmation |
| **STT Transcription**   | Unit tested with `MockSTTEngine`          | Faster-Whisper on CPU/CUDA         | Need live PCM audio streaming from participant       |
| **NMT Fan-Out**         | Unit tested with `MockNMTEngine`          | Meta NLLB-200 / IndicTrans2        | Need model weights loaded in worker container        |
| **TTS Audio Egress**    | Local frame counting in memory            | AudioSource WebRTC publication     | Need `livekit.rtc` native publisher                  |
| **WebSocket Resync**    | Unit tested with static snapshot          | Multi-client disconnect/reconnect  | Need monotonic sequence counter in gateway           |
| **Multi-Tenant RLS**    | Tested with mock session and RLS SQL      | Real multi-tenant Postgres queries | Proven in `test_security_audit.py`                   |

---

## 4. Required Runtime Evidence Packages (Prior to GA Release)

Before declaring any PR or the final platform complete, the following physical evidence packages must be captured and logged in `docs/release/`:

1. **Vertical Slice A Proof**: Real browser speaks in Hindi $\to$ Backend transcribes $\to$ Translates to English $\to$ LiveKit AudioSource publishes $\to$ Listener browser plays English audio.
2. **Vertical Slice B Proof**: Speaker speaks Hindi $\to$ Listener 1 receives English audio $\to$ Listener 2 receives Marathi audio $\to$ Neither receives unintended synthetic audio.
3. **Vertical Slice C Proof**: Three-way conversation (Hindi, English, Japanese) with concurrent fan-out and independent listener selections.
4. **Vertical Slice D Proof**: Reconnection during active chat and captions $\to$ WebSocket resync frame restores state without gap or duplicate.
5. **Vertical Slice E Proof**: AI worker outage during live call $\to$ Human audio continues uninterrupted $\to$ Worker restored $\to$ Normal translation resumes without audio burst.
