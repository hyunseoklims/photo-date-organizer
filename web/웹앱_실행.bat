@echo off
setlocal
cd /d "%~dp0"

py -3 -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo Python is required to run the local web server.
    echo Install Python, then run this file again.
    pause
    exit /b 1
)

echo Starting local web server at http://localhost:8765
start "" "http://localhost:8765"
py -3 -m http.server 8765
