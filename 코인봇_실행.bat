@echo off
chcp 65001 >nul
cd /d %~dp0
title 코인 자동매매 봇

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       코인 자동매매 봇 v1.0  시작 중...                 ║
echo  ║  업비트 + 바이비트  ^|  김프차익  ^|  AI 자동매매          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ── 바탕화면 단축아이콘 자동 생성 ───────────────────────────────────────────
set SHORTCUT="%USERPROFILE%\Desktop\코인봇.lnk"
if not exist %SHORTCUT% (
    echo Set oShell = CreateObject("WScript.Shell") > "%TEMP%\mklink.vbs"
    echo Set oLink = oShell.CreateShortcut(%SHORTCUT%) >> "%TEMP%\mklink.vbs"
    echo oLink.TargetPath = "%~f0" >> "%TEMP%\mklink.vbs"
    echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\mklink.vbs"
    echo oLink.Description = "코인 자동매매 봇" >> "%TEMP%\mklink.vbs"
    echo oLink.Save >> "%TEMP%\mklink.vbs"
    cscript //nologo "%TEMP%\mklink.vbs"
    del "%TEMP%\mklink.vbs"
    echo  [+] 바탕화면에 단축아이콘 생성 완료!
)

:: ── Python 확인 ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [오류] Python이 설치되어 있지 않습니다.
    echo  https://www.python.org 에서 Python 3.10 이상을 설치하세요.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [+] Python %PYVER% 감지됨

:: ── .env 파일 확인 ───────────────────────────────────────────────────────────
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo  [!] .env 파일이 없어서 자동으로 생성했습니다.
        echo  [!] .env 파일을 열어 API 키를 입력한 후 다시 실행하세요.
        echo.
        echo  .env 파일을 지금 열겠습니까? (Y/N)
        set /p OPEN_ENV=  ^> 
        if /i "%OPEN_ENV%"=="Y" notepad .env
        echo.
        echo  API 키 입력 후 이 창을 닫고 다시 실행하세요.
        pause
        exit /b 0
    )
)

:: ── 패키지 설치 ──────────────────────────────────────────────────────────────
echo  [+] 필요한 패키지 설치 중... (처음 실행 시 시간이 걸릴 수 있습니다)
python -m pip install -r crypto_bot_requirements.txt -q --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  [오류] 패키지 설치 실패. 인터넷 연결을 확인하세요.
    pause
    exit /b 1
)
echo  [+] 패키지 준비 완료

:: ── 서버 실행 ────────────────────────────────────────────────────────────────
echo.
echo  [+] 서버 시작 중... 잠시 후 브라우저가 자동으로 열립니다.
echo  [+] 종료하려면 이 창을 닫거나 Ctrl+C 를 누르세요.
echo.
python run_bot.py

echo.
echo  봇이 종료되었습니다.
pause
