@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 build.py %*) else (python build.py %*)
if errorlevel 1 (
  echo.
  echo Сборка не удалась. Подробности выше.
)
pause
