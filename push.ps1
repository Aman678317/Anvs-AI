Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "1. Running Unit Tests and Verification Gates..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tests failed! Aborting git commit and push." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "2. Running Ruff Lint Check..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ruff linting failed! Aborting git commit and push." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "3. All checks passed! Staging, committing, and pushing..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

git add -A
git commit -m "feat(core): PR-01 fail-fast invariants, PR-06 v1.2 lineage, PR-08 state resync, PR-09 hardening"
git push origin HEAD

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Process complete! Successfully tested and pushed to origin HEAD." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
