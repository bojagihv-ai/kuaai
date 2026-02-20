#!/bin/bash
# 코인 자동매매 봇 런처 (Mac/Linux)
cd "$(dirname "$0")"

echo ""
echo " ╔══════════════════════════════════════════════════════════╗"
echo " ║       코인 자동매매 봇 v1.0  시작 중...                 ║"
echo " ║  업비트 + 바이비트 | 김프차익 | AI 자동매매             ║"
echo " ╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Python 확인 ───────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo " [오류] python3 가 설치되어 있지 않습니다."
    echo " brew install python3  또는  apt install python3 으로 설치하세요."
    read -p " 계속하려면 Enter..."
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo " [+] $PYVER 감지됨"

# ── .env 파일 확인 ────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo " [!] .env 파일을 자동 생성했습니다."
        echo " [!] .env 파일에 API 키를 입력한 후 다시 실행하세요."
        echo ""
        read -p " .env 파일을 지금 열겠습니까? (y/N): " OPEN_ENV
        if [[ "$OPEN_ENV" =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
        echo ""
        echo " API 키 입력 후 스크립트를 다시 실행하세요."
        read -p " 계속하려면 Enter..."
        exit 0
    fi
fi

# ── 패키지 설치 ───────────────────────────────────────────────────────────────
echo " [+] 필요한 패키지 설치 중..."
python3 -m pip install -r crypto_bot_requirements.txt -q 2>&1 | tail -3
echo " [+] 패키지 준비 완료"

# ── 서버 실행 ─────────────────────────────────────────────────────────────────
echo ""
echo " [+] 서버 시작 중... 잠시 후 브라우저가 열립니다."
echo " [+] 종료: Ctrl+C"
echo ""
python3 run_bot.py

echo ""
echo " 봇이 종료되었습니다."
read -p " 계속하려면 Enter..."
