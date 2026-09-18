@echo off
cd /d "%~dp0"
py -3.13 -m pip install -r requirements.txt 
py -3.13 launcher.py
pause
