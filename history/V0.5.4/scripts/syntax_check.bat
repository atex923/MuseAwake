@echo off
cd /d "%~dp0..\source"
py -m py_compile "MouseAwake_V0.5.4.py"
if errorlevel 1 (
    echo.
    echo Syntax check FAILED.
    pause
    exit /b 1
)
echo.
echo Syntax check OK.
pause
