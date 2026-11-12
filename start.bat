@echo off
rem Starts Fair Share. Needs Python 3.9 or newer.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 fairshare.py %*) else (python fairshare.py %*)
if errorlevel 1 echo. & echo If Python is missing, get 3.9 or newer from https://www.python.org/downloads/
pause
