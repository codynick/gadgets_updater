@echo off
cd /d "%~dp0"
py -c "import serial, tkinter" >nul 2>&1
if errorlevel 1 (
  echo Python with tkinter and pyserial is required.
  echo Install Python, then run: py -m pip install -r requirements.txt
  pause
  exit /b 1
)
py app\app.py
if errorlevel 1 pause
