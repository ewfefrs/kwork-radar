"""Генератор черновика отклика по шаблонам (без LLM).

Черновик — это ЗАГОТОВКА. Прочитай ТЗ, поправь под конкретный заказ и
отправь руками на Kwork. Никакого автопостинга.
"""
from __future__ import annotations

from .models import Project

# Определение типа заказа по словам в заголовке/описании.
_KIND_RULES = [
    ("bot", ["бот", "bot", "telegram", "телеграм", "whatsapp", "ватсап", "вайбер", "chatbot"]),
    ("android", ["андроид", "android", "kotlin", "мобильн", "приложение", "apk", "google play"]),
    ("parser", ["парсер", "парсинг", "parsing", "scraping", "спарс", "собрать данные", "выгруз"]),
    ("integration", ["api", "интеграц", "n8n", "webhook", "автоматизац", "crm", "google sheets", "таблиц"]),
]

# Короткая отсылка к твоему реальному опыту под тип заказа.
_CASE = {
    "bot": "Делал Telegram-ботов под задачи (приём заявок, авто-ответы, интеграции с таблицами и API) — например, @Whispromptbot и мульти-бот для сервиса вызова нянь (TG + WhatsApp).",
    "android": "Android/Kotlin-разработчик. Из свежего — Whisprompt: телесуфлёр для смарт-очков Even Realities G2 (BLE-протокол, свой движок отрисовки), плюс порт на iOS.",
    "parser": "Пишу парсеры/сборщики данных на Python (в т.ч. по сайтам с защитой и динамикой через headless-браузер), с выгрузкой в нужный формат.",
    "integration": "Собираю автоматизации и интеграции: связки API, боты, n8n-сценарии, выгрузки в Google Sheets/CRM — под ключ.",
    "other": "Разработчик: Android/Kotlin, Python, Telegram-боты, парсеры и автоматизация. Берусь за задачи, где нужно быстро и по делу.",
}

# По 2 варианта заготовки на тип — просто чтобы тебе было из чего выбрать.
_OPENERS = {
    0: "Здравствуйте! По задаче «{title}» — готов взяться и довести до результата.",
    1: "Здравствуйте! Прочитал ТЗ «{title}», задача понятна, могу сделать.",
}

_TAIL = (
    "Чтобы назвать точные срок и цену, уточню пару моментов: {questions}\n\n"
    "Портфолио и связь: {portfolio}"
)

_QUESTIONS = {
    "bot": "на какой платформе принимаем сообщения и куда их складывать (таблица/CRM/почта)?",
    "android": "нужен готовый дизайн/макет или на мне тоже, и под какие версии Android?",
    "parser": "какой источник(и) парсим, какие поля нужны и в каком формате выгрузка?",
    "integration": "какие системы связываем и что считаем итогом (куда падают данные)?",
    "other": "что считаем готовым результатом и есть ли жёсткий дедлайн?",
}


def detect_kind(project: Project) -> str:
    text = f"{project.title} {project.description}".lower()
    for kind, words in _KIND_RULES:
        if any(w in text for w in words):
            return kind
    return "other"


def build_draft(project: Project, portfolio_url: str) -> str:
    kind = detect_kind(project)
    project.kind = kind

    variant = int(project.id) % 2
    opener = _OPENERS[variant].format(title=project.title.strip())
    case = _CASE[kind]
    tail = _TAIL.format(
        questions=_QUESTIONS[kind],
        portfolio=portfolio_url or "(добавь ссылку на портфолио в .env)",
    )
    return f"{opener}\n\n{case}\n\n{tail}"
