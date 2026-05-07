@echo off
REM ============================================================
REM Build LingProps Desktop standalone .exe
REM
REM Prereqs (one-time):
REM   pip install pyinstaller lingprops streamlit pandas openpyxl
REM   pip install spacy
REM   python -m spacy download en_core_web_sm
REM
REM Output:
REM   dist\LingProps.exe   - single-file standalone executable
REM
REM Optional: build the Inno Setup installer afterwards by running
REM   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
REM ============================================================

setlocal
cd /d "%~dp0"

echo ================================================================
echo Cleaning previous build artefacts...
echo ================================================================
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo.
echo ================================================================
echo Running PyInstaller...
echo ================================================================
pyinstaller lingprops_app.spec --noconfirm

if errorlevel 1 (
    echo.
    echo *** PyInstaller failed.  See output above. ***
    exit /b 1
)

echo.
echo ================================================================
echo Build complete.
echo   Output: dist\LingProps.exe
echo ================================================================

REM Optional: build the installer if Inno Setup is present
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo.
    echo Building installer with Inno Setup...
    %ISCC% installer.iss
) else (
    echo.
    echo Skipping installer build  -  Inno Setup not found at %ISCC%
    echo Install from https://jrsoftware.org/isdl.php to enable.
)

endlocal
