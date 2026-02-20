#!/usr/bin/env python3
"""Entry point for the crypto trading bot."""
import os
import sys
import time
import threading
import webbrowser
import uvicorn
from pathlib import Path

# ── .env 처리 ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
env_path = BASE_DIR / ".env"
env_example = BASE_DIR / ".env.example"

# .env 없으면 .env.example 복사 안내
if not env_path.exists() and env_example.exists():
    import shutil
    shutil.copy(env_example, env_path)
    print("[!] .env 파일을 자동 생성했습니다.")
    print("[!] .env 파일에 업비트/바이비트 API 키를 입력하세요.")
    print()

try:
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print("[+] .env 파일 로드됨")
except ImportError:
    pass  # python-dotenv 없어도 동작

PORT = int(os.getenv("BOT_PORT", 8000))
HOST = os.getenv("BOT_HOST", "0.0.0.0")
RELOAD = os.getenv("BOT_DEV", "false").lower() == "true"
URL = f"http://localhost:{PORT}"


def open_browser():
    """서버 시작 후 2초 뒤 브라우저 자동 오픈."""
    time.sleep(2.5)
    webbrowser.open(URL)
    print(f"[+] 브라우저 자동 오픈: {URL}")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║       코인 자동매매 봇 v1.0  (Ctrl+C 로 종료)           ║
║  업비트 + 바이비트 | 김프차익 | AI 자동매매              ║
╠══════════════════════════════════════════════════════════╣""")
    print(f"║  대시보드 → {URL:<46}║")
    print(f"║  API 문서 → {URL}/docs{' '*39}║")
    print("""╚══════════════════════════════════════════════════════════╝
    """)

    # 브라우저 자동 오픈 (백그라운드 스레드)
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "crypto_bot.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info",
    )
