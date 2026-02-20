#!/usr/bin/env python3
"""Entry point for the crypto trading bot."""
import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[+] .env 파일 로드됨")
else:
    print("[!] .env 파일 없음 - .env.example 참고하여 생성하세요")

PORT = int(os.getenv("BOT_PORT", 8000))
HOST = os.getenv("BOT_HOST", "0.0.0.0")
RELOAD = os.getenv("BOT_DEV", "false").lower() == "true"

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║         코인 자동매매 봇 v1.0                            ║
║  업비트 + 바이비트 | 김프차익 | AI 자동매매              ║
╠══════════════════════════════════════════════════════════╣
║  대시보드 → http://localhost:{PORT:<5}                      ║
║  API 문서 → http://localhost:{PORT:<5}/docs                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(
        "crypto_bot.app:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info",
    )
