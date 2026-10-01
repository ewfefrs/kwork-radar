"""Сбор ленты заказов Kwork через headless-браузер (Playwright).

Почему браузер, а не requests: Kwork отдаёт карточки только после исполнения
JS / прохождения reCAPTCHA v3, в «сыром» HTML их нет. Поэтому нужен настоящий
Chromium. Читаем только публичную ленту, мягко, с паузами.
"""
from __future__ import annotations

import asyncio
import logging
import random
from urllib.parse import quote

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .models import Project
from .parsing import BASE, EXTRACT_JS, parse_card

log = logging.getLogger("radar.fetcher")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class KworkFetcher:
    def __init__(self, headful: bool = False):
        self._headful = headful
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None
        self._page: Page | None = None

    async def _launch(self) -> Browser:
        assert self._pw is not None
        headless = not self._headful
        # Сначала пробуем СИСТЕМНЫЙ Chrome — у него все зависимости уже на месте
        # (встроенный Chromium может падать из-за нехватки VC++ Redistributable).
        try:
            return await self._pw.chromium.launch(channel="chrome", headless=headless)
        except Exception as exc:  # noqa: BLE001
            log.warning("Системный Chrome не стартовал (%s). Пробую встроенный Chromium.", exc)
            return await self._pw.chromium.launch(headless=headless)

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._launch()
        self._ctx = await self._browser.new_context(
            user_agent=UA,
            locale="ru-RU",
            viewport={"width": 1280, "height": 900},
        )
        self._page = await self._ctx.new_page()
        log.info("Браузер запущен (headless=%s)", not self._headful)

    async def close(self) -> None:
        for closer in (self._ctx, self._browser):
            try:
                if closer:
                    await closer.close()
            except Exception:
                pass
        if self._pw:
            await self._pw.stop()

    async def _fetch_keyword(self, keyword: str) -> list[Project]:
        assert self._page is not None
        url = f"{BASE}/projects?keyword={quote(keyword)}"
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await self._page.wait_for_selector(".want-card", timeout=12000)
            except Exception:
                log.info("По «%s» карточек нет (или не прогрузились)", keyword)
                return []
            raw = await self._page.evaluate(EXTRACT_JS)
        except Exception as exc:  # noqa: BLE001
            log.warning("Ошибка загрузки по «%s»: %s", keyword, exc)
            return []

        projects = [p for p in (parse_card(r) for r in raw) if p]
        log.info("По «%s»: %d заказов", keyword, len(projects))
        return projects

    async def fetch(self, keywords: list[str]) -> list[Project]:
        """Тянет ленту по всем ключевикам, отдаёт уникальные заказы по id."""
        seen: dict[str, Project] = {}
        for kw in keywords:
            for p in await self._fetch_keyword(kw):
                seen.setdefault(p.id, p)
            await asyncio.sleep(random.uniform(1.0, 2.5))  # мягкий интервал
        return list(seen.values())
