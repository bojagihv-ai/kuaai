"""Persistence layer for run snapshots + product state tracking."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config import config

DB_PATH: Path = config.sqlite_path
JSON_PATH: Path = config.latest_json_path


def _ensure_storage() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                run_at TEXT,
                product_id TEXT,
                name_zh TEXT,
                translated_name TEXT,
                price_cny REAL,
                cogs REAL,
                sale_price REAL,
                gross_margin REAL,
                coupang_competitors INTEGER,
                keyword TEXT,
                product_url TEXT,
                image_url TEXT,
                selected INTEGER,
                is_new INTEGER,
                registration_status TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS product_state (
                product_id TEXT PRIMARY KEY,
                first_seen_at TEXT,
                last_seen_at TEXT,
                last_competitors INTEGER,
                last_selected INTEGER,
                last_registration_status TEXT
            )
            """
        )


def save_results(
    raw_products: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    new_only: list[dict[str, Any]],
) -> None:
    _ensure_storage()
    run_at = datetime.utcnow().isoformat()

    selected_ids = {p.get("product_id") for p in selected}
    new_ids = {p.get("product_id") for p in new_only}

    rows: list[dict[str, Any]] = []
    for p in raw_products:
        rows.append(
            {
                "run_at": run_at,
                "product_id": p.get("product_id"),
                "name_zh": p.get("name_zh"),
                "translated_name": p.get("translated_name"),
                "price_cny": p.get("price_cny"),
                "cogs": p.get("cogs"),
                "sale_price": p.get("sale_price"),
                "gross_margin": p.get("gross_margin"),
                "coupang_competitors": p.get("coupang_competitors"),
                "keyword": p.get("keyword"),
                "product_url": p.get("product_url"),
                "image_url": p.get("image_url"),
                "selected": int(p.get("product_id") in selected_ids),
                "is_new": int(p.get("product_id") in new_ids),
                "registration_status": p.get("registration_status", "PENDING"),
            }
        )

    with sqlite3.connect(DB_PATH) as conn:
        pd.DataFrame(rows).to_sql("products", conn, if_exists="append", index=False)
        for row in rows:
            conn.execute(
                """
                INSERT INTO product_state (
                    product_id, first_seen_at, last_seen_at,
                    last_competitors, last_selected, last_registration_status
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    last_competitors=excluded.last_competitors,
                    last_selected=excluded.last_selected,
                    last_registration_status=excluded.last_registration_status
                """,
                (
                    row["product_id"],
                    run_at,
                    run_at,
                    row["coupang_competitors"],
                    row["selected"],
                    row["registration_status"],
                ),
            )
        conn.commit()

    JSON_PATH.write_text(
        json.dumps(
            {
                "run_at": run_at,
                "raw_count": len(raw_products),
                "selected_count": len(selected),
                "new_count": len(new_only),
                "items": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
