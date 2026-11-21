@echo off
chcp 65001 >nul
echo === Building Sound.Widget.Overlay.exe ===
python -m pip install --upgrade pyinstaller PyQt6 winsdk
if errorlevel 1 goto :fail

python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name "Sound.Widget.Overlay" ^
  --collect-all winsdk ^
  sound_widget_overlay.py
if errorlevel 1 goto :fail

echo.
echo Done:  dist\Sound.Widget.Overlay.exe
pause
exit /b 0

:fail
echo Build failed.
pause
exit /b 1
