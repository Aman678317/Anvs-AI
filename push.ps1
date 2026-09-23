Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "1. Auto-formatting with Prettier (TS/JS/MD/JSON/YAML)..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pnpm run format
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Warning: pnpm run format exited with code $LASTEXITCODE, trying npx prettier..." -ForegroundColor Yellow
    npx prettier --write "**/*.{ts,tsx,js,jsx,json,md,yml,yaml}"
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "2. Auto-formatting Python Code with Ruff..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

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
Write-Host "4. Running Unit and Contract Test Suites..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py tests/contract/test_event_contracts.py tests/unit/test_livekit_audio_subscriber.py tests/unit/test_audio_ingress_service.py tests/unit/test_audio_ingestion.py tests/unit/test_stt_worker.py tests/unit/test_translation_worker.py tests/contract/test_translation_contracts.py tests/unit/test_tts_worker.py tests/contract/test_tts_contracts.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tests failed! Aborting git commit and push." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "5. Staging, Committing, and Pushing to HEAD..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

git add -A
git commit -m "feat(pr-11-pr-12): nmt fanout glossary dec-01 registry and real livekit tts audio egress timing"
git push origin HEAD

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Process complete! Successfully formatted, tested, and pushed to origin HEAD." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
