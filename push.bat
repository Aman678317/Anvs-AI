@echo off
echo =====================================================
echo 1. Auto-formatting Python Code with Ruff...
echo =====================================================

ruff format .

echo =====================================================
echo 2. Verifying Ruff Format ^& Lint Checks...
echo =====================================================

ruff format --check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff format check failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

ruff check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff lint check failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 3. Running Unit and Contract Test Suites...
echo =====================================================

pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py tests/contract/test_event_contracts.py -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unit tests failed! Aborting.
    pause
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 4. Staging, Committing, and Pushing to HEAD...
echo =====================================================

git add -A
git commit -m "style: format code with ruff 0.6.9 and enforce CI parity"
git push origin HEAD

echo.
echo =====================================================
echo Process complete! Successfully formatted, tested, and pushed to origin HEAD.
echo =====================================================
pause
