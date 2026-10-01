"""Тесты чистой логики. Запуск:  python tests\test_logic.py
Ничего не качает из сети и не требует pytest."""
from __future__ import annotations

import sys
from pathlib import Path

try:  # корректный вывод кириллицы в Windows-консоли
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar.config import Config
from radar.drafts import build_draft, detect_kind
from radar.matcher import evaluate, is_relevant
from radar.parsing import parse_card, rub_amounts


def _cfg(min_budget=1500, max_offers=5):
    return Config(
        bot_token="x", chat_id=1, poll_min=60, poll_max=150,
        portfolio_url="https://t.me/test", min_budget=min_budget,
        max_notify=10, max_offers=max_offers, tg_proxy="", headful=False,
    )


# ── Реальные образцы карточек (как их отдаёт DOM Kwork) ──────────────────
CARD_FRESH_BOT = {
    "url": "/projects/3246999",
    "title": "Бот для автоматического создания карточек в Trello",
    "desc": "Нужен бот (Telegram или n8n-сценарий)... Показать полностью",
    "price": "Желаемый бюджет: до 5 000 ₽ Допустимый: до 15 000 ₽",
    "meta": ("Бот для автоматического создания карточек в Trello Желаемый бюджет: "
             "до 5 000 ₽ Допустимый: до 15 000 ₽ Покупатель: zhukovmedia77 "
             "Размещено проектов на бирже: 4 Нанято: 0% Осталось: 1 д. 23 ч. Предложений: 0"),
}

CARD_VIDEO = {
    "url": "/projects/3246861",
    "title": "Техническое задание: монтаж 12 шортсов",
    "desc": "Нужно смонтировать 12 продающих вертикальных шортсов... Показать полностью",
    "price": "Цена до: 2 000 ₽",
    "meta": ("монтаж 12 шортсов Цена до: 2 000 ₽ Покупатель: Pronyagin_alex "
             "Размещено проектов на бирже: 182 Нанято: 93% Осталось: 23 ч. 59 мин. Предложений: 0"),
}

CARD_NO_URL = {"url": None, "title": "нет ссылки", "desc": "", "price": "", "meta": ""}

# «Работа» содержит подстроку «бот» — проверяем, что границы слова спасают.
CARD_WORK_SMM = {
    "url": "/projects/3229160",
    "title": "Работа с соцсетями — массовые отметки пользователей",
    "desc": "Нужно проставить отметки и пригласить друзей... Показать полностью",
    "price": "до 10 000 ₽",
    "meta": ("Работа с соцсетями массовые отметки до 10 000 ₽ Покупатель: smm1 "
             "Размещено проектов на бирже: 5 Нанято: 33% Осталось: 23 ч. Предложений: 0"),
}

_results = []


def check(name: str, cond: bool) -> None:
    _results.append((name, cond))
    print(("  OK  " if cond else " FAIL ") + name)


def run() -> int:
    # rub_amounts
    check("rub: две суммы", rub_amounts("до 5 000 ₽ и 15 000 ₽") == [5000, 15000])
    check("rub: пусто", rub_amounts("без цены") == [])

    # parse_card
    bot = parse_card(CARD_FRESH_BOT)
    check("parse: id", bot.id == "3246999")
    check("parse: url", bot.url == "https://kwork.ru/projects/3246999")
    check("parse: желаемый бюджет", bot.budget_desired == 5000)
    check("parse: макс бюджет", bot.budget_max == 15000)
    check("parse: budget property = макс", bot.budget == 15000)
    check("parse: откликов 0", bot.offers == 0)
    check("parse: заказчик", bot.buyer == "zhukovmedia77")
    check("parse: проектов заказчика", bot.buyer_projects == 4)
    check("parse: срок", "1 д. 23 ч." in bot.time_left and "Предложени" not in bot.time_left)
    check("parse: нет ссылки → None", parse_card(CARD_NO_URL) is None)

    vid = parse_card(CARD_VIDEO)
    check("parse: одна цена → desired=max", vid.budget_desired == 2000 and vid.budget_max == 2000)
    check("parse: hire rate 93", vid.buyer_hire_rate == 93)

    # detect_kind
    check("kind: бот", detect_kind(bot) == "bot")
    check("kind: видео → other", detect_kind(vid) == "other")

    # Границы слова: «бот» не должен ловиться в «работа».
    from radar.matcher import has_dev_signal
    work = parse_card(CARD_WORK_SMM)
    check("boundary: 'бот' не ловит 'работа'",
          has_dev_signal(work, _cfg().strong_include) is False)

    # is_relevant / exclude
    cfg = _cfg(min_budget=1500)
    check("relevant: бот проходит", is_relevant(bot, cfg) is True)
    check("relevant: монтаж/шортс отсеян", is_relevant(vid, cfg) is False)
    check("relevant: SMM-отметки отсеяны", is_relevant(work, cfg) is False)

    # Фильтр по минимуму откликов: тот же бот, но с 50 откликами — отсеять.
    busy = parse_card({**CARD_FRESH_BOT,
                       "meta": CARD_FRESH_BOT["meta"].replace("Предложений: 0", "Предложений: 50")})
    check("relevant: много откликов отсеяно", is_relevant(busy, cfg) is False)
    check("relevant: 0 откликов проходит", is_relevant(bot, cfg) is True)

    # Лидоген «найти клиентов» отсекаем, даже если есть dev-слово в описании.
    leadgen = parse_card({
        "url": "/projects/999", "title": "Необходимо найти клиентов",
        "desc": "нужна автоматизация поиска, есть api", "price": "до 200 000 ₽",
        "meta": "до 200 000 ₽ Покупатель: x Осталось: 1 д. Предложений: 2",
    })
    check("relevant: 'найти клиентов' отсеяно", is_relevant(leadgen, cfg) is False)

    # Требование юр-статуса/аккредитации — отсекаем, хоть это и разработка.
    orgreq = parse_card({
        "url": "/projects/1000", "title": "Разработка Telegram-бота",
        "desc": "нужен разработчик с аккредитацией, оплата на ИП",
        "price": "до 50 000 ₽",
        "meta": "до 50 000 ₽ Покупатель: y Осталось: 1 д. Предложений: 1",
    })
    check("relevant: требование аккредитации/ИП отсеяно", is_relevant(orgreq, cfg) is False)
    check("relevant: дешёвый отсеян",
          is_relevant(parse_card({**CARD_FRESH_BOT, "price": "до 500 ₽",
                                  "meta": CARD_FRESH_BOT["meta"].replace("15 000", "500").replace("5 000", "500")}),
                      _cfg(min_budget=1500)) is False)

    # score: свежий дорогой бот должен быть высоким
    evaluate(bot, cfg)
    check("score: высокий у свежего дорогого", bot.score >= 80)

    # build_draft
    draft = build_draft(bot, cfg.portfolio_url)
    check("draft: содержит заголовок", "Trello" in draft)
    check("draft: содержит портфолио", "https://t.me/test" in draft)
    check("draft: kind проставлен", bot.kind == "bot")

    ok = sum(1 for _, c in _results if c)
    total = len(_results)
    print(f"\n{ok}/{total} прошло")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(run())
