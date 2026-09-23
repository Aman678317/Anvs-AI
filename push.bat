@echo off
echo =====================================================
echo 1. Running Unit Tests and Verification Gates...
echo =====================================================

pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py -v
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo =====================================================
    echo [ERROR] Unit tests failed! Aborting git commit and push.
    echo =====================================================
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 2. Running Ruff Lint Check...
echo =====================================================

ruff check .
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo =====================================================
    echo [ERROR] Ruff lint failed! Aborting git commit and push.
    echo =====================================================
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 3. All checks passed! Staging, committing, and pushing...
echo =====================================================

git add -A
git commit -m "feat(core): PR-01 fail-fast invariants, PR-06 v1.2 lineage, PR-08 state resync, PR-09 hardening"
git push origin HEAD

echo.
echo =====================================================
echo Process complete! Successfully tested and pushed to origin HEAD.
echo =====================================================
pause
