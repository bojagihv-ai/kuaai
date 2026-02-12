from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None

from app.core.settings import settings
from app.schemas.contracts import CompetitorStructure


@dataclass
class CompetitorAnalyzer:
    def analyze_from_url(self, url: str) -> CompetitorStructure:
        html = self._fetch_playwright(url) or self._fetch_html(url)
        if not html:
            return self._fallback("url fetch failed, use manual upload mode")
        soup = BeautifulSoup(html, "html.parser")
        headers = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:8]
        blocks = [tag.name for tag in soup.find_all(["section", "article", "ul", "ol", "blockquote"])][:10]
        tone = self._infer_tone_from_text(" ".join(headers))
        return CompetitorStructure(
            source="url",
            layout=["hero", "benefits grid", "proof band", "offer module", "faq accordion"],
            sectioning=headers or ["Hero", "Benefits", "Proof", "Offer", "FAQ"],
            tone=tone,
            notes=f"Structure-only analysis from {url}; never reuse source text/images.",
        )

    def analyze_from_assets(self, asset_paths: Iterable[str]) -> CompetitorStructure:
        names = [Path(p).name for p in asset_paths]
        return CompetitorStructure(
            source="manual_assets",
            layout=["hero", "feature stack", "comparison", "social proof", "faq"],
            sectioning=[f"Manual asset: {name}" for name in names] or ["Manual competitor evidence provided"],
            tone=["informative", "confident"],
            notes="Manual input mode used due to scraping limits.",
        )


    def _fetch_playwright(self, url: str) -> str:
        if sync_playwright is None:
            return ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=settings.user_agent)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=settings.scraper_timeout_s * 1000)
                content = page.content()
                browser.close()
                return content
        except Exception:
            return ""

    def _fetch_html(self, url: str) -> str:
        try:
            with httpx.Client(timeout=settings.scraper_timeout_s, headers={"User-Agent": settings.user_agent}, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception:
            return ""

    def _infer_tone_from_text(self, text: str) -> list[str]:
        lowered = text.lower()
        tone = ["clear"]
        if any(w in lowered for w in ["save", "deal", "discount"]):
            tone.append("promotional")
        if any(w in lowered for w in ["science", "test", "lab", "certified"]):
            tone.append("evidence-led")
        if len(tone) == 1:
            tone.append("educational")
        return tone

    def _fallback(self, reason: str) -> CompetitorStructure:
        return CompetitorStructure(
            source="fallback",
            layout=["hero", "problem", "solution", "proof", "faq"],
            sectioning=["Hero", "Problem", "Solution", "Proof", "FAQ"],
            tone=["friendly", "direct"],
            notes=reason,
        )
