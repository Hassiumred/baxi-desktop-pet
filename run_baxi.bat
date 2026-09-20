@echo off
setlocal
cd /d "%~dp0"
python tools\check_asset_presence.py
if errorlevel 1 exit /b 2
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python app\main.py
