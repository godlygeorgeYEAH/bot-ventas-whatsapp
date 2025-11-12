@echo off
cd /d "C:\work\work\Context Bot V2\bot-ventas-whatsapp"
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo Starting bot...
python run.py -v

