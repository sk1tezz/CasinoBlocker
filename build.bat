@echo off
pip install -r requirements.txt
REM Сборка CasinoBlocker в .exe (требуется: pip install pyinstaller)
pyinstaller --onefile --noconsole --icon=NONE --name CasinoBlocker main.py
echo.
echo Готово: dist\CasinoBlocker.exe
pause
