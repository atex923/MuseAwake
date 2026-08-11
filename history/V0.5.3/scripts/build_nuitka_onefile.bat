\
    @echo off
    setlocal
    cd /d "%~dp0..\source"

    echo ========================================
    echo MouseAwake V0.5.3 - Nuitka Onefile Build
    echo ========================================
    echo.

    py -m nuitka ^
      --mode=onefile ^
      --windows-console-mode=disable ^
      --enable-plugin=tk-inter ^
      --assume-yes-for-downloads ^
      --output-filename=MouseAwake_V0.5.3.exe ^
      "MouseAwake_V0.5.3.pyw"

    echo.
    if errorlevel 1 (
        echo Build FAILED.
    ) else (
        echo Build completed.
    )
    pause
    endlocal
