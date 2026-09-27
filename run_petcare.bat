@echo off
REM PetCare+ Launcher — starts the PySide6 desktop app
REM Run from the repository root (where this file lives)

set PROJECT_ROOT=%~dp0
set PYTHONPATH=%PROJECT_ROOT%

REM Activate venv and launch
call "%PROJECT_ROOT%\.venv\Scripts\activate.bat" >nul 2>&1
python -m app.__main__

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
)