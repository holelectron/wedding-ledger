@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto location_failed
title Wedding Ledger Setup
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "SETUP_LOG=%~dp0setup.log"
echo Wedding Ledger Setup > "%SETUP_LOG%"
echo Installing Wedding Ledger...
echo Log: "%SETUP_LOG%"
if not exist "app.py" goto files_missing
if not exist "requirements.txt" goto files_missing
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or later is required'" >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
py -3 -m venv .venv >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
goto install
:python
where python >nul 2>nul
if errorlevel 1 goto missing
python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or later is required'" >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
python -m venv .venv >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
:install
echo Checking Python and installing required packages...
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or later is required'" >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -c "import tkinter, PIL; import app; r=tkinter.Tk(); r.withdraw(); app.configure_fonts(r); app.rounded_buttons(r,app.ttk.Style(r)); r.destroy(); print('Startup checks passed')" >> "%SETUP_LOG%" 2>&1
if errorlevel 1 goto failed
if not exist ".venv\Scripts\pythonw.exe" goto failed
echo.
echo Setup completed successfully.
if /i "%~1"=="--check" exit /b 0
echo Press any key to open the program. This setup window will then close.
pause >nul
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py"
if errorlevel 1 goto failed
exit /b 0
:files_missing
echo Required files are missing. Extract the entire downloaded ZIP first. >> "%SETUP_LOG%"
goto failed
:missing
echo Python was not found. Install Python 3.11 or later. >> "%SETUP_LOG%"
echo https://www.python.org/downloads/windows/ >> "%SETUP_LOG%"
echo Enable Add python.exe to PATH during installation. >> "%SETUP_LOG%"
goto failed
:failed
echo.
echo Setup failed. Details:
type "%SETUP_LOG%"
echo.
echo The error was saved to setup.log in this folder.
if /i "%~1"=="--check" exit /b 1
echo Press any key to close this window.
pause >nul
exit /b 1
:location_failed
echo Cannot open the program folder. Extract the ZIP to a writable local folder.
pause
exit /b 1
