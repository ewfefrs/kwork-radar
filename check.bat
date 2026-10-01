@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo === Проверка парсинга (без Telegram) ===
python -m radar --dry-run
pause
