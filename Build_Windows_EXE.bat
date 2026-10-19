@echo off
cd /d "%~dp0"
echo Building the GUI EXE. Internet required for build dependencies.
py -m pip install pyinstaller -r requirements.txt
if errorlevel 1 goto failed
if not exist build mkdir build
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CodyNick_Gadgets_Updater --distpath . --workpath build\work --specpath build --add-data "%~dp0app\gateway_v6.hex;." --add-data "%~dp0app\bootloader_profiles;bootloader_profiles" "%~dp0app\app.py"
if errorlevel 1 goto failed
echo Built: %~dp0CodyNick_Gadgets_Updater.exe
echo Keep the EXE here beside firmware and docs. AVRDUDE remains required.
pause
exit /b 0
:failed
echo Build failed. Keep the output for diagnosis.
pause
exit /b 1
