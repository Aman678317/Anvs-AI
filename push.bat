@echo off
echo =====================================================
echo 0. Eradicating Legacy Duplicate Trees & Dead Artifacts...
echo =====================================================

if exist "services\assistant-worker" rd /s /q "services\assistant-worker"
if exist "services\realtime-gateway" rd /s /q "services\realtime-gateway"
if exist "services\speaker-worker" rd /s /q "services\speaker-worker"
if exist "services\stt-worker" rd /s /q "services\stt-worker"
if exist "services\translation-worker" rd /s /q "services\translation-worker"
if exist "services\tts-worker" rd /s /q "services\tts-worker"
if exist "services\voice-worker" rd /s /q "services\voice-worker"
if exist "packages\event-schema" rd /s /q "packages\event-schema"
if exist "packages\language-registry" rd /s /q "packages\language-registry"
if exist "packages\contracts\models.py" del /f /q "packages\contracts\models.py"
if exist "apps\web\src\index.ts" del /f /q "apps\web\src\index.ts"
if exist "apps\admin\src\index.ts" del /f /q "apps\admin\src\index.ts"
if exist "ai-content-agent.db" del /f /q "ai-content-agent.db"

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

call pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_websocket_manager.py tests/unit/test_auth_router.py tests/unit/test_livekit_service.py tests/unit/test_livekit_webhooks.py tests/contract/test_event_contracts.py tests/unit/test_livekit_audio_subscriber.py tests/unit/test_audio_ingress_service.py tests/unit/test_audio_ingestion.py tests/unit/test_stt_worker.py tests/unit/test_translation_worker.py tests/contract/test_translation_contracts.py tests/unit/test_tts_worker.py tests/contract/test_tts_contracts.py tests/chaos/test_pipeline_chaos_resilience.py tests/load/test_load_concurrency.py tests/unit/test_assistant_worker.py tests/unit/test_assistant_memory.py tests/contract/test_assistant_contracts.py tests/realtime/test_websocket_realtime_lifecycle.py tests/integration/test_platform_integration.py tests/integration/test_vertical_slices.py tests/security/test_security_audit.py -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 5. Staging, Committing, and Pushing to HEAD...
echo =====================================================

git add -A
git commit -m "feat: integrate Supabase/NVIDIA NIM, fix error propagation, strengthen ticket verification, and refresh audit docs"
git push origin HEAD

echo.
echo =====================================================
echo Process complete! Successfully formatted, tested, and pushed to origin HEAD.
echo =====================================================
pause
