@echo off
setlocal

python -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --collect-all keyring ^
  --name g2b_alert ^
  main.py

echo.
echo Build complete. Check dist\g2b_alert.exe
echo Run the exe once to create config.json, data, and logs automatically.

if exist build rmdir /s /q build
if exist g2b_alert.spec del /q g2b_alert.spec
if exist dist\config.json del /q dist\config.json
if exist dist\config.example.json del /q dist\config.example.json

pause
