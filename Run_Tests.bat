@echo off
cd /d "%~dp0"
py -m unittest discover -s app -p "test_*.py" -v
pause
