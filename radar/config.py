"""Загрузка конфигурации из .env и настроек фильтра."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Простой парсер .env без внешних зависимостей."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Не перетираем то, что уже задано в окружении.
        os.environ.setdefault(key, value)


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


# ─── Ключевые слова для ПОИСКА по ленте Kwork ───────────────────────────
# Радар делает по одному запросу /projects?keyword=<слово> на каждый пункт.
# Поиск Kwork широкий, поэтому итог ещё фильтруется списками ниже.
DEFAULT_KEYWORDS = [
    "андроид", "android", "kotlin", "приложение",
    "бот", "telegram bot", "телеграм бот",
    "парсер", "парсинг", "scraping",
    "автоматизация", "n8n", "api", "интеграция",
    "mvp", "бэкенд",
]

# ОБЯЗАТЕЛЬНЫЙ сигнал разработки: заказ проходит, только если в заголовке/
# описании есть хотя бы одно из этих слов (сопоставление по началу слова,
# с учётом границы — «бот» НЕ ловит «работа»).
DEFAULT_STRONG_INCLUDE = [
    "разработ", "программ", "андроид", "android", "kotlin", "java",
    "ios", "swift", "flutter", "python", "джанго", "django",
    "бот", "chatbot", "чат-бот", "telegram-бот",
    "парсер", "парсинг", "parsing", "scraping", "спарс", "спарсить",
    "api", "интеграц", "автоматизац", "n8n", "webhook", "вебхук",
    "сайт", "лендинг", "вёрстк", "верстк", "backend", "бэкенд", "фронтенд",
    "приложение", "mvp", "скрипт", "база данных", "sql", "crm",
]

# СТОП-СЛОВА: если совпало — заказ отбрасывается (SMM, накрутки, серые
# ручные задачи, контент/монтаж — не твоя тематика).
DEFAULT_EXCLUDE = [
    "отметк", "пригласить", "друзей", "подписчик", "подписот",
    "накрут", "лайк", "просмотр", "буст", "голосован", "проголосов",
    "продаж", "отзыв", "коммент", "смм", "smm", "таргетолог",
    "монтаж", "смонтир", "шортс", "reels", "рилс", "клип",
    "копирайт", "рерайт", "рерайтинг", "обзвон", "оператор call",
    "наполнение", "регистрац аккаунт", "накликать", "кликов",
    # Лидоген / продажи / поиск клиентов — не разработка.
    "найти клиент", "поиск клиент", "привлеч клиент", "привлечение клиент",
    "нужны клиент", "нужен клиент", "лидоген", "лиды", "холодная база",
    "менеджер по продаж", "продажник", "sales manager",
    # Требования к юр-статусу / аккредитации / организации — не для частника.
    "аккредит", "самозанят", "нужно ип", "нужен ип", "требуется ип",
    "оплата на ип", "оформлен ип", "только ооо", "нужно ооо", "юр лицо",
    "юрлицо", "юридическое лицо", "с ндс", "плательщик ндс", "в штат",
    "штатн", "трудоустройств", "по тк рф", "гражданство рф", "резидент рф",
]


@dataclass
class Config:
    bot_token: str
    chat_id: int
    poll_min: int
    poll_max: int
    portfolio_url: str
    min_budget: int
    max_notify: int
    max_offers: int
    tg_proxy: str
    headful: bool
    keywords: list[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    strong_include: list[str] = field(default_factory=lambda: list(DEFAULT_STRONG_INCLUDE))
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    db_path: Path = ROOT / "radar_state.db"

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv(ROOT / ".env")
        return cls(
            bot_token=_get("BOT_TOKEN"),
            chat_id=_get_int("CHAT_ID", 0),
            poll_min=_get_int("POLL_MIN_SECONDS", 60),
            poll_max=_get_int("POLL_MAX_SECONDS", 150),
            portfolio_url=_get("PORTFOLIO_URL", ""),
            min_budget=_get_int("MIN_BUDGET", 1500),
            max_notify=_get_int("MAX_NOTIFY", 10),
            max_offers=_get_int("MAX_OFFERS", 5),
            tg_proxy=_get("TG_PROXY", ""),
            headful=_get("HEADFUL", "0") == "1",
        )

    def validate(self) -> list[str]:
        problems = []
        if not self.bot_token or self.bot_token.startswith("123456789:"):
            problems.append("BOT_TOKEN не задан (получи у @BotFather).")
        if not self.chat_id:
            problems.append("CHAT_ID не задан (узнай у @userinfobot).")
        if self.poll_min > self.poll_max:
            problems.append("POLL_MIN_SECONDS больше POLL_MAX_SECONDS.")
        return problems
