@echo off
setlocal

python -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --collect-all keyring ^
  --add-data "g2b_alert\assets\icons;g2b_alert\assets\icons" ^
  --add-data "g2b_alert\assets\Pretendard-1.3.9\LICENSE.txt;g2b_alert\assets\Pretendard-1.3.9" ^
  --add-data "g2b_alert\assets\Pretendard-1.3.9\public\static\Pretendard-Regular.otf;g2b_alert\assets\Pretendard-1.3.9\public\static" ^
  --add-data "g2b_alert\assets\Pretendard-1.3.9\public\static\Pretendard-Medium.otf;g2b_alert\assets\Pretendard-1.3.9\public\static" ^
  --add-data "g2b_alert\assets\Pretendard-1.3.9\public\static\Pretendard-SemiBold.otf;g2b_alert\assets\Pretendard-1.3.9\public\static" ^
  --add-data "g2b_alert\assets\Pretendard-1.3.9\public\static\Pretendard-Bold.otf;g2b_alert\assets\Pretendard-1.3.9\public\static" ^
  --name g2b_alert ^
  main.py

echo.
echo Build complete. Check dist\g2b_alert.exe
echo Run the exe once to create config.json, data, and logs under %%LOCALAPPDATA%%\G2BAlert.

if exist build rmdir /s /q build
if exist g2b_alert.spec del /q g2b_alert.spec
if exist dist\config.json del /q dist\config.json
if exist dist\config.example.json del /q dist\config.example.json

pause
