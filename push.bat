@echo off
echo =====================================================
echo 1. Auto-formatting with Prettier (TS/JS/MD/JSON/YAML)...
echo =====================================================

call pnpm run format
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] pnpm run format failed, trying npx prettier...
    call npx prettier --write "**/*.{ts,tsx,js,jsx,json,md,yml,yaml}"
)

echo =====================================================
echo 2. Auto-formatting Python Code with Ruff...
echo =====================================================

call ruff format .

echo =====================================================
echo 3. Verifying Prettier ^& Ruff Quality Gates...
echo =====================================================

call pnpm run format:check
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Prettier format check failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

call ruff format --check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff format check failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

call ruff check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff lint check failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 4. Running Unit and Contract Test Suites...
echo =====================================================

call pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py tests/unit/test_livekit_webhooks.py tests/contract/test_event_contracts.py tests/unit/test_livekit_audio_subscriber.py tests/unit/test_audio_ingress_service.py tests/unit/test_audio_ingestion.py tests/unit/test_stt_worker.py tests/unit/test_translation_worker.py tests/contract/test_translation_contracts.py tests/unit/test_tts_worker.py tests/contract/test_tts_contracts.py tests/chaos/test_pipeline_chaos_resilience.py tests/unit/test_assistant_worker.py tests/unit/test_assistant_memory.py tests/contract/test_assistant_contracts.py tests/realtime/test_websocket_realtime_lifecycle.py tests/integration/test_platform_integration.py tests/integration/test_vertical_slices.py tests/security/test_security_audit.py -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 5. Staging, Committing, and Pushing to HEAD...
echo =====================================================

git add -A
git commit -m "feat(pr-15): production hardening ga certification vertical slices and realtime lifecycle suites"
git push origin HEAD

echo.
echo =====================================================
echo Process complete! Successfully formatted, tested, and pushed to origin HEAD.
echo =====================================================
pause
