"""Отправка уведомлений в Telegram (aiogram v3)."""
from __future__ import annotations

import html

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .models import Project


def make_bot(token: str, proxy: str = "") -> Bot:
    session = AiohttpSession(proxy=proxy) if proxy else None
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def _rub(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " ₽"


def _budget_line(p: Project) -> str:
    if p.budget_desired and p.budget_max and p.budget_desired != p.budget_max:
        return f"{_rub(p.budget_desired)} – {_rub(p.budget_max)}"
    if p.budget:
        return f"до {_rub(p.budget)}"
    return "бюджет не указан"


def _fire(score: int) -> str:
    if score >= 80:
        return "🔥🔥🔥"
    if score >= 60:
        return "🔥🔥"
    return "🔥"


def format_message(p: Project, draft: str) -> str:
    buyer = html.escape(p.buyer or "—")
    buyer_stats = []
    if p.buyer_hire_rate:
        buyer_stats.append(f"найм {p.buyer_hire_rate}%")
    if p.buyer_projects:
        buyer_stats.append(f"проектов {p.buyer_projects}")
    buyer_line = f"👤 {buyer}" + (f" ({', '.join(buyer_stats)})" if buyer_stats else "")

    return (
        f"{_fire(p.score)} <b>{p.score}</b> · {html.escape(p.title)}\n\n"
        f"💰 {_budget_line(p)}   ·   💬 откликов: <b>{p.offers}</b>\n"
        f"⏳ {html.escape(p.time_left or '—')}\n"
        f"{buyer_line}\n\n"
        f"✍️ Черновик (нажми — скопируется целиком):\n"
        f"<pre>{html.escape(draft)}</pre>"
    )


def keyboard(project: Project) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            # Кнопка-ссылка: открывает заказ на Kwork напрямую (работает всегда).
            [InlineKeyboardButton(text="🔗 Открыть на Kwork", url=project.url)],
            [
                InlineKeyboardButton(text="✅ Откликнулся", callback_data=f"applied:{project.id}"),
                InlineKeyboardButton(text="🚫 Скип", callback_data=f"skipped:{project.id}"),
            ],
        ]
    )


async def send_project(bot: Bot, chat_id: int, project: Project, draft: str) -> None:
    await bot.send_message(
        chat_id,
        format_message(project, draft),
        reply_markup=keyboard(project),
        disable_web_page_preview=True,
    )
