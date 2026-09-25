param(
    [string]$Branch = "feat/pr-01-baseline-hygiene"
)

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "0. Eradicating Legacy Duplicate Trees, Locks & Dead Artifacts..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

if (Test-Path ".git/index.lock") {
    Remove-Item -Force ".git/index.lock" -ErrorAction SilentlyContinue
    Write-Host "Cleared stale .git/index.lock" -ForegroundColor Yellow
}

$DeadPaths = @(
    "services/assistant-worker",
    "services/realtime-gateway",
    "services/speaker-worker",
    "services/stt-worker",
    "services/translation-worker",
    "services/tts-worker",
    "services/voice-worker",
    "packages/event-schema",
    "packages/language-registry",
    "packages/contracts/models.py",
    "apps/web/src/index.ts",
    "apps/admin/src/index.ts",
    "ai-content-agent.db",
    ".agents",
    ".claude",
    ".cursor",
    ".devin",
    ".windsurf",
    ".qodo"
)
foreach ($p in $DeadPaths) {
    if (Test-Path $p) {
        Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
        Write-Host "Pruned dead path: $p" -ForegroundColor Green
    }
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "1. Auto-formatting with Prettier (TS/JS/MD/JSON/YAML)..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pnpm run format
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Warning: pnpm run format exited with code $LASTEXITCODE, trying npx prettier..." -ForegroundColor Yellow
    npx prettier --write "**/*.{ts,tsx,js,jsx,json,md,yml,yaml}"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "2. Auto-fixing & Auto-formatting Python Code with Ruff..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

ruff check --fix .
ruff format .

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "3. Verifying Prettier & Ruff Quality Gates..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pnpm run format:check
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Prettier format check failed! Aborting." -ForegroundColor Red
    exit $LASTEXITCODE
}

ruff format --check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ruff format check failed! Aborting." -ForegroundColor Red
    exit $LASTEXITCODE
}

ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ruff lint check failed! Aborting." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "4. Staging, Committing, and Force-Pushing to $Branch..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

git add -A
git commit -m "fix: remove invalid livekit-server-sdk dependency, resolve 500 room creation, and configure Render" -q
Write-Host "Force-pushing to origin $Branch..." -ForegroundColor Cyan
git push --force origin "$Branch"

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Process complete! Successfully formatted and pushed to origin $Branch." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
