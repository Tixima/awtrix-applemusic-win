@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python fehlt. Von https://www.python.org/downloads/ installieren.
  echo Dabei "Add python.exe to PATH" ankreuzen.
  pause
  exit /b 1
)
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Pakete konnten nicht installiert werden.
  pause
  exit /b 1
)
py -3 itunes-helper.py --install %*
echo.
pause
