@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:python
where python >nul 2>nul
if errorlevel 1 goto missing
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
start "" wscript.exe "%~dp0½ÇÇà.vbs"
exit /b 0
:missing
echo Install Python 3.11 or later from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH", then run setup.bat again.
pause
exit /b 1
:failed
echo Setup failed. Check the error above and run setup.bat again.
pause
exit /b 1
