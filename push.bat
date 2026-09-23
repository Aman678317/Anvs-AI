@echo off
echo =====================================================
echo Staging, committing, and pushing all changes to Git...
echo =====================================================

git add -A
git commit -m "feat(web): multi-guest WebRTC mesh video calling, VAD speaker halo, live speech captions, and WhatsApp call sharing"
git push origin HEAD

echo.
echo =====================================================
echo Process complete! Pushed to origin HEAD.
echo =====================================================
pause
