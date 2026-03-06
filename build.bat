@echo off
REM Сборка CasinoBlocker в .exe (требуется: pip install pyinstaller)
pyinstaller --onefile --noconsole --name CasinoBlocker main.py
echo.
echo Готово: dist\CasinoBlocker.exe
pause
