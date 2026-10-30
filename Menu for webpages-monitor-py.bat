@echo off
REM Interactive start menu for the webpages monitor.
REM Asks which mode to run, then starts webpages_monitor.py accordingly.
setlocal
chcp 65001 >nul
REM This file lives in the project folder next to webpages_monitor.py.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python.exe not found in PATH.
    pause
    goto end
)

:menu
cls
echo ============================================
echo   Menu for webpage-monitor-py
echo ============================================
echo.
echo   1  Check now        (--force: fetch and compare all webpages, send mail)
echo   2  Send test mail   (--test-mail: mail with the current daily report)
echo   3  Show help        (--help: command line options)
echo   4  Daily report     (REPORT-daily-summary.txt)
echo   5  Run report       (REPORT-of-every-run-last-3-days.txt)
echo   0  Exit
echo.
choice /c 123450 /n /m "Select [1-5, 0]: "
set "selection=%ERRORLEVEL%"

if "%selection%"=="1" set "args=--force"
if "%selection%"=="2" set "args=--test-mail"
if "%selection%"=="3" set "args=--help"
if "%selection%"=="4" goto show_daily
if "%selection%"=="5" goto show_runs
if "%selection%"=="6" goto end
goto run

:show_daily
if exist "REPORT-daily-summary.txt" (
    start "" notepad "REPORT-daily-summary.txt"
) else (
    echo.
    echo No daily report yet.
    pause
)
goto menu

:show_runs
if exist "REPORT-of-every-run-last-3-days.txt" (
    start "" notepad "REPORT-of-every-run-last-3-days.txt"
) else (
    echo.
    echo No run report yet.
    pause
)
goto menu

:run
echo.
echo Running: python webpages_monitor.py %args%
echo --------------------------------------------
python webpages_monitor.py %args%
echo --------------------------------------------
echo Exit code: %ERRORLEVEL%  (0 = no change, 1 = change/error, 2 = run failed)
echo.
choice /c yn /n /m "Back to menu? [y/n]: "
if errorlevel 2 goto end
goto menu

:end
endlocal
