Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "1. Auto-formatting Python Code with Ruff..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

ruff format .

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "2. Verifying Ruff Format & Lint Checks..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

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
Write-Host "3. Running Unit and Contract Test Suites..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

pytest tests/unit/test_settings.py tests/unit/test_event_schemas.py tests/unit/test_websocket_gateway.py tests/unit/test_livekit_service.py tests/contract/test_event_contracts.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tests failed! Aborting git commit and push." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "4. Staging, Committing, and Pushing to HEAD..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

git add -A
git commit -m "style: format code with ruff 0.6.9 and enforce CI parity"
git push origin HEAD

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Process complete! Successfully formatted, tested, and pushed to origin HEAD." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
