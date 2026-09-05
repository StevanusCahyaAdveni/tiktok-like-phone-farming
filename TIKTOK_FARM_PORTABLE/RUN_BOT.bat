@echo off
title TikTok Multi-Device Farm Engine
cd /d "%~dp0"
echo ===================================================
echo   TIKTOK MULTI-DEVICE FARM ENGINE (PORTABLE)
echo ===================================================
echo Memeriksa Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan di sistem ini!
    echo Silakan install Python 3.10+ dan centang 'Add Python to PATH'.
    pause
    exit /b 1
)

echo Memeriksa dependensi uiautomator2...
python -c "import uiautomator2" >nul 2>nul
if %errorlevel% neq 0 (
    echo Menginstal uiautomator2...
    pip install uiautomator2
)

echo Menjalankan Bot TikTok Farm Engine...
python tiktok_auto_allInOne_lab.py
pause
