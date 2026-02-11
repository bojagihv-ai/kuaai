"""Slack/email notifications."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

import requests

from config import config


def notify_slack(text: str) -> None:
    if not config.slack_webhook:
        return
    try:
        requests.post(
            config.slack_webhook,
            json={"text": text},
            timeout=config.request_timeout_sec,
            headers={"User-Agent": config.user_agent},
        )
    except requests.RequestException:
        return


def notify_email(subject: str, body: str) -> None:
    if not config.notification_email:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "bot@example.com"
    msg["To"] = config.notification_email
    msg.set_content(body)

    try:
        with smtplib.SMTP("localhost", 25, timeout=10) as smtp:
            smtp.send_message(msg)
    except OSError:
        return


def notify_new_products(products: list[dict[str, Any]]) -> None:
    preview = "\n".join(
        f"- {p.get('translated_name', p.get('name_zh', 'unknown'))} / 경쟁:{p.get('coupang_competitors', 0)}"
        for p in products[:10]
    )
    text = f"새 상품 {len(products)}개 발견\n{preview}"
    notify_slack(text)
    notify_email("[봇] 새 상품 발견", text)


def send_notification(item: dict[str, Any], response: dict[str, Any]) -> None:
    name = item.get("translated_name", item.get("name_zh", "unknown"))
    text = f"등록 결과 - {name}: {response}"
    notify_slack(text)
    notify_email(f"[봇] 등록 결과 - {name}", text)
