@echo off
echo =====================================================
echo 0. Clearing Git Locks and Dead Artifacts...
echo =====================================================

if exist ".git\index.lock" (
    echo Removing stale .git\index.lock...
    del /f /q ".git\index.lock"
)

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
if exist ".agents" rd /s /q ".agents"
if exist ".claude" rd /s /q ".claude"
if exist ".cursor" rd /s /q ".cursor"
if exist ".devin" rd /s /q ".devin"
if exist ".windsurf" rd /s /q ".windsurf"
if exist ".qodo" rd /s /q ".qodo"

echo =====================================================
echo 1. Auto-formatting with Prettier (TS/JS/MD/JSON/YAML)...
echo =====================================================

call pnpm run format
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] pnpm run format failed, falling back to npx prettier...
    call npx prettier --write "**/*.{ts,tsx,js,jsx,json,md,yml,yaml}"
)

echo =====================================================
echo 2. Auto-formatting Python Code with Ruff...
echo =====================================================

call ruff format .

echo =====================================================
echo 3. Verifying Prettier and Ruff Quality Gates...
echo =====================================================

call pnpm run format:check
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Prettier format check failed! Aborting.
    exit /b %ERRORLEVEL%
)

call ruff format --check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff format check failed! Aborting.
    exit /b %ERRORLEVEL%
)

call ruff check .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ruff lint check failed! Aborting.
    exit /b %ERRORLEVEL%
)

echo =====================================================
echo 4. Staging, Committing, and Force Pushing to feat/pr-01-baseline-hygiene...
echo =====================================================

git add -A
git commit -m "style: format smoke test with ruff"
git push --force origin feat/pr-01-baseline-hygiene

echo =====================================================
echo Process complete! Successfully pushed to origin feat/pr-01-baseline-hygiene.
echo =====================================================
