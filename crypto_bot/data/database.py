"""SQLite database for persisting trades, signals, config."""
import sqlite3
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "crypto_bot_data.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange    TEXT NOT NULL,
            symbol      TEXT NOT NULL,
            side        TEXT NOT NULL,
            price       REAL NOT NULL,
            qty         REAL NOT NULL,
            amount_krw  REAL NOT NULL,
            fee         REAL NOT NULL,
            pnl         REAL DEFAULT 0,
            order_id    TEXT,
            strategy    TEXT DEFAULT 'auto',
            note        TEXT,
            dry_run     INTEGER DEFAULT 1,
            timestamp   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange    TEXT,
            symbol      TEXT,
            signal      TEXT,
            score       REAL,
            price       REAL,
            indicators  TEXT,
            timestamp   REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS arbitrage (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            kimchi_pct      REAL,
            net_profit_pct  REAL,
            direction       TEXT,
            upbit_price     REAL,
            bybit_price_krw REAL,
            usd_krw         REAL,
            amount_krw      REAL,
            profit_krw      REAL,
            status          TEXT,
            timestamp       REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS config (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL
        );
        """)
    logger.info(f"Database initialized at {DB_PATH}")


def save_trade(exchange: str, symbol: str, side: str, price: float, qty: float,
               amount_krw: float, fee: float, pnl: float = 0, order_id: str = "",
               strategy: str = "auto", note: str = "", dry_run: bool = True):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO trades (exchange,symbol,side,price,qty,amount_krw,fee,pnl,
               order_id,strategy,note,dry_run,timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (exchange, symbol, side, price, qty, amount_krw, fee, pnl,
             order_id, strategy, note, int(dry_run), time.time()),
        )


def get_trades(limit: int = 100, strategy: str = None) -> list[dict]:
    with get_conn() as conn:
        if strategy:
            rows = conn.execute(
                "SELECT * FROM trades WHERE strategy=? ORDER BY timestamp DESC LIMIT ?",
                (strategy, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def save_signal(exchange: str, symbol: str, signal: str, score: float,
                price: float, indicators: dict):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO signals (exchange,symbol,signal,score,price,indicators,timestamp) VALUES (?,?,?,?,?,?,?)",
            (exchange, symbol, signal, score, price, json.dumps(indicators), time.time()),
        )


def save_arbitrage(kimchi_pct: float, net_profit_pct: float, direction: str,
                   upbit_price: float, bybit_price_krw: float, usd_krw: float,
                   amount_krw: float, profit_krw: float, status: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO arbitrage (kimchi_pct,net_profit_pct,direction,upbit_price,
               bybit_price_krw,usd_krw,amount_krw,profit_krw,status,timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (kimchi_pct, net_profit_pct, direction, upbit_price, bybit_price_krw,
             usd_krw, amount_krw, profit_krw, status, time.time()),
        )


def save_config(key: str, value):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )


def load_config(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        if row:
            return json.loads(row["value"])
    return default


def get_pnl_summary() -> dict:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN side='sell' AND pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN side='sell' AND pnl <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                SUM(fee) as total_fee
            FROM trades WHERE dry_run=0
        """).fetchone()
        arb_row = conn.execute("""
            SELECT SUM(profit_krw) as arb_profit, COUNT(*) as arb_trades
            FROM arbitrage WHERE status='executed'
        """).fetchone()
    return {
        "total_trades": row["total_trades"] or 0,
        "wins": row["wins"] or 0,
        "losses": row["losses"] or 0,
        "win_rate": (row["wins"] or 0) / max(row["total_trades"] or 1, 1) * 100,
        "total_pnl": row["total_pnl"] or 0,
        "total_fee": row["total_fee"] or 0,
        "net_pnl": (row["total_pnl"] or 0) - (row["total_fee"] or 0),
        "arb_profit": arb_row["arb_profit"] or 0,
        "arb_trades": arb_row["arb_trades"] or 0,
    }
