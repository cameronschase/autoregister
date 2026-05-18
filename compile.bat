@echo off
REM ============================================================
REM  ONE-TIME BUILD SCRIPT
REM
REM  Run this once on a Windows machine that has Python installed.
REM  It will produce dist\extract_data.exe, a standalone executable
REM  you can copy to any Windows machine and double-click to run.
REM ============================================================

cd /d "%~dp0"

echo Checking for Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not on PATH.
    echo Install Python from https://www.python.org/downloads/
    echo and check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo.
echo Installing build requirements...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyinstaller requests beautifulsoup4 pandas openpyxl
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo Building standalone executable... (this takes 1-2 minutes)
REM --onefile    = single .exe (no folder of DLLs alongside)
REM --console    = keep the black window so user sees prompts and output
REM --name       = name of the output .exe
REM --clean      = wipe PyInstaller's cache for a clean build
python -m PyInstaller --onefile --console --clean --name extract_data extract_data.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Build complete!
echo.
echo Your executable is at:    dist\extract_data.exe
echo.
echo Copy that one file anywhere; double-click to use.
echo No Python install needed on the target machine.
echo ============================================================
echo.
pause