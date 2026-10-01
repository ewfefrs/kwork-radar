@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo === Установка Kwork Radar ===
echo.

py -3 -m venv venv
if errorlevel 1 (
  echo Не найден Python. Установи Python 3.11+ с python.org и поставь галочку "Add to PATH".
  pause
  exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

echo.
echo === Готово! ===
echo 1) Скопируй  .env.example  в  .env
echo 2) Впиши в .env свои BOT_TOKEN и CHAT_ID
echo 3) Проверь парсинг:  check.bat
echo 4) Запусти боевой режим:  run.bat
echo.
pause
