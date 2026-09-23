Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "Staging, committing, and pushing all changes to Git..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

git add -A
git commit -m "feat(web): multi-guest WebRTC mesh video calling, VAD speaker halo, live speech captions, and WhatsApp call sharing"
git push origin HEAD

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "Process complete! Pushed to origin HEAD." -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
