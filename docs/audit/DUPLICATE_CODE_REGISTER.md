# ANVS-AI Multilingual Meeting Platform — Duplicate Code Register (Phase 0)

> **Document**: `docs/audit/DUPLICATE_CODE_REGISTER.md`  
> **Author**: Lead Principal Software Engineer & QA Lead  
> **Date**: September 22, 2026  
> **Purpose**: Registry of parallel/duplicate directory trees, canonical naming selection, and eradication roadmap.

---

## 1. Problem Statement

The repository contains multiple duplicate directory trees where services and packages exist in both **hyphenated** (`kebab-case`) and **underscored** (`snake_case`) versions.

In Python, module names containing hyphens cannot be imported using standard `import foo-bar` syntax (causing `SyntaxError`). This led to an ad-hoc bifurcation where underscored directories were created for Python imports while some hyphenated directories were left as legacy stubs or partial copies.

---

## 2. Duplicate Pairs Inventory & Canonical Selection

| Duplicate Directory (Hyphenated) | Canonical Directory (Underscored) | Status / Contents Analysis | Decision |
| :--- | :--- | :--- | :--- |
| `services/assistant-worker/` | `services/assistant_worker/` | Hyphenated dir has only `__init__.py` (626 bytes). Underscored dir has full implementation (`consumer.py`, `engine.py`, `main.py`, etc.). | **DELETE** `services/assistant-worker/`<br>**RETAIN** `services/assistant_worker/` |
| `services/realtime-gateway/` | `services/realtime_gateway/` | Hyphenated dir has 5 stub files with only 1-line docstrings (e.g. `main.py` is 54 bytes). Underscored dir has full implementation (`manager.py`, `server.py`, `subscriber.py`). | **DELETE** `services/realtime-gateway/`<br>**RETAIN** `services/realtime_gateway/` |
| `services/speaker-worker/` | `services/speaker_worker/` | Hyphenated dir has only `__init__.py` (618 bytes). Underscored dir has full PyAnnote engine and consumer. | **DELETE** `services/speaker-worker/`<br>**RETAIN** `services/speaker_worker/` |
| `services/stt-worker/` | `services/stt_worker/` | Hyphenated dir has only `__init__.py` (503 bytes). Underscored dir has full Faster-Whisper engine, audio consumer, language utils. | **DELETE** `services/stt-worker/`<br>**RETAIN** `services/stt_worker/` |
| `services/translation-worker/` | `services/translation_worker/` | Hyphenated dir has only `__init__.py` (555 bytes). Underscored dir has full NLLB translation engine, batch consumer, and models. | **DELETE** `services/translation-worker/`<br>**RETAIN** `services/translation_worker/` |
| `services/tts-worker/` | `services/tts_worker/` | Hyphenated dir has only `__init__.py` (357 bytes). Underscored dir has Piper/Bark TTS engine, ultrasonic watermark injector, consumer. | **DELETE** `services/tts-worker/`<br>**RETAIN** `services/tts_worker/` |
| `packages/event-schema/` | `packages/event_schema/` | Exact duplicate byte-for-byte copies of `__init__.py` (1021 bytes), `bus.py` (6589 bytes), and `events.py` (5766 bytes). | **DELETE** `packages/event-schema/`<br>**RETAIN** `packages/event_schema/` |
| `packages/language-registry/` | `packages/language_registry/` | Exact duplicate copies of `languages.py` (5943 bytes). Hyphenated dir `__init__.py` is 500 bytes vs 507 bytes in underscored dir. | **DELETE** `packages/language-registry/`<br>**RETAIN** `packages/language_registry/` |

---

## 3. Special Case: `services/voice-worker`

Notice that `services/voice-worker` exists, but **neither** a hyphenated complete version **nor** an underscored `services/voice_worker` version exists!
- `services/voice-worker` contains only a 48-byte stub `__init__.py`.
- **Decision**: In **PR-01**, rename/create canonical `services/voice_worker/` with proper module structure and remove `services/voice-worker/`. In **PR-11**, implement the full voice preservation and cloning worker.

---

## 4. Root Cause of Import Discrepancies

In `pyproject.toml` and Docker configurations:
- Some Dockerfiles referenced hyphenated service directories (e.g., `COPY services/stt-worker`).
- Some test fixtures imported from hyphenated names or used dynamic imports to work around Python syntax limitations.

Standardizing on **underscore notation** across all Python packages aligns with:
- PEP 8 (Package and Module Names: "Modules should have short, all-lowercase names. Underscores can be used in the module name if it improves readability. Python packages should also have all-lowercase names, although the use of underscores is discouraged.")
- PEP 508 / Poetry / Hatch standard python packaging conventions.

---

## 5. Eradication Action Plan (PR-01)

1. Remove all 8 legacy hyphenated directories:
   - `services/assistant-worker/`
   - `services/realtime-gateway/`
   - `services/speaker-worker/`
   - `services/stt-worker/`
   - `services/translation-worker/`
   - `services/tts-worker/`
   - `packages/event-schema/`
   - `packages/language-registry/`
2. Migrate `services/voice-worker/` to canonical `services/voice_worker/`.
3. Update any Dockerfiles, Helm charts, or configuration files referencing hyphenated directory paths to use canonical underscore paths.
4. Verify all tests and imports resolve cleanly using canonical paths.
