@echo off
rem Serves AssaultCube on http://localhost:8000 (needs Python 3). Close this window to stop.
cd /d "%~dp0"
echo AssaultCube: open http://localhost:8000
python -m http.server 8000 --bind 127.0.0.1 || py -m http.server 8000 --bind 127.0.0.1
pause
