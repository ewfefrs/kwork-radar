"""Оркестрация: цикл опроса + Telegram-бот с кнопками."""
from __future__ import annotations

import asyncio
import logging
import random

from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery

from .config import Config
from .drafts import build_draft
from .fetcher import KworkFetcher
from .matcher import evaluate, is_relevant
from .notifier import format_message, make_bot, send_project
from .state import State

log = logging.getLogger("radar")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def poll_once(cfg: Config, fetcher: KworkFetcher, state: State, bot, dry_run: bool) -> int:
    """Один проход: собрать ленту, отобрать новые релевантные, уведомить."""
    projects = await fetcher.fetch(cfg.keywords)

    fresh = []
    for p in projects:
        # В dry-run базу не трогаем — показываем всё релевантное каждый раз.
        if not dry_run and state.is_seen(p.id):
            continue
        if not is_relevant(p, cfg):
            continue
        fresh.append(evaluate(p, cfg))

    # Меньше всего откликов — в самый верх (свежак без конкуренции),
    # при равенстве — по оценке «горячести».
    fresh.sort(key=lambda x: (x.offers, -x.score))
    # Лимит на цикл, чтобы не заваливать. Остаток «сольётся» в следующих циклах.
    to_send = fresh if dry_run else fresh[: cfg.max_notify]
    log.info(
        "Собрано %d заказов, новых релевантных: %d, отправляю: %d",
        len(projects), len(fresh), len(to_send),
    )

    for p in to_send:
        draft = build_draft(p, cfg.portfolio_url)
        if dry_run:
            print("\n" + "=" * 70)
            print(format_message(p, draft))
        else:
            try:
                await send_project(bot, cfg.chat_id, p, draft)
            except Exception as exc:  # noqa: BLE001
                log.error("Не удалось отправить в Telegram: %s", exc)
                continue
            state.add(p)  # помечаем как показанное только реально отправленные
    return len(to_send)


async def _poll_loop(cfg: Config, fetcher: KworkFetcher, state: State, bot) -> None:
    while True:
        try:
            await poll_once(cfg, fetcher, state, bot, dry_run=False)
        except Exception as exc:  # noqa: BLE001
            log.exception("Ошибка в цикле опроса: %s", exc)
        delay = random.uniform(cfg.poll_min, cfg.poll_max)
        log.info("Следующий опрос через %d сек", int(delay))
        await asyncio.sleep(delay)


async def run(dry_run: bool = False, once: bool = False) -> None:
    _setup_logging()
    cfg = Config.load()

    problems = cfg.validate()
    if problems and not dry_run:
        print("⛔ Проблемы с конфигом (.env):")
        for pr in problems:
            print("  •", pr)
        print("\nИсправь .env и запусти снова. Для проверки парсинга без Telegram: --dry-run")
        return

    state = State(cfg.db_path)
    fetcher = KworkFetcher(cfg.headful)
    await fetcher.start()

    bot = None if dry_run else make_bot(cfg.bot_token, cfg.tg_proxy)

    try:
        # Разовый прогон или dry-run — без запуска бота-диспетчера.
        if dry_run or once:
            n = await poll_once(cfg, fetcher, state, bot, dry_run=dry_run)
            log.info("Готово. Новых заказов: %d", n)
            return

        # Боевой режим: диспетчер (для кнопок) + фоновый цикл опроса.
        dp = Dispatcher()

        @dp.callback_query(F.data.startswith("applied:"))
        async def on_applied(cb: CallbackQuery) -> None:
            state.set_status(cb.data.split(":", 1)[1], "applied")
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.answer("Отмечено: откликнулся ✅")

        @dp.callback_query(F.data.startswith("skipped:"))
        async def on_skipped(cb: CallbackQuery) -> None:
            state.set_status(cb.data.split(":", 1)[1], "skipped")
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.answer("Пропущено 🚫")

        await bot.send_message(cfg.chat_id, "📡 Kwork Radar запущен. Слежу за лентой.")
        poll_task = asyncio.create_task(_poll_loop(cfg, fetcher, state, bot))
        try:
            await dp.start_polling(bot)
        finally:
            poll_task.cancel()
    finally:
        await fetcher.close()
        state.close()
        if bot is not None:
            await bot.session.close()
