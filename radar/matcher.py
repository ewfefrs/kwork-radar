"""Фильтр релевантности и скоринг «горячести» заказа.

Матчинг — по началу слова с учётом левой границы: «бот» ловит «бот/бота/
боты», но НЕ «работа»; «api» ловит «API», но не «capital».
"""
from __future__ import annotations

import re
from functools import lru_cache

from .config import Config
from .models import Project


@lru_cache(maxsize=16)
def _compile(terms: tuple[str, ...]) -> re.Pattern | None:
    parts = [re.escape(t.lower().strip()) for t in terms if t.strip()]
    if not parts:
        return None
    # (?<!\w) — левая граница слова; \w в Python включает кириллицу.
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")", re.IGNORECASE)


def _text(project: Project) -> str:
    return f"{project.title}\n{project.description}".lower()


def is_excluded(project: Project, exclude: list[str]) -> bool:
    rx = _compile(tuple(exclude))
    return bool(rx and rx.search(_text(project)))


def has_dev_signal(project: Project, strong_include: list[str]) -> bool:
    rx = _compile(tuple(strong_include))
    return bool(rx and rx.search(_text(project)))


def is_relevant(project: Project, cfg: Config) -> bool:
    """Проходит, если: не в стоп-словах, есть сигнал разработки, бюджет ок,
    и откликов не больше лимита (ловим свежак, пока конкурентов мало)."""
    if is_excluded(project, cfg.exclude):
        return False
    if not has_dev_signal(project, cfg.strong_include):
        return False
    if cfg.min_budget and project.budget and project.budget < cfg.min_budget:
        return False
    if cfg.max_offers and project.offers > cfg.max_offers:
        return False
    return True


def score(project: Project, cfg: Config) -> int:
    """Оценка 0–100: чем свежее, дороже и адекватнее заказчик — тем выше."""
    pts = 30  # база

    # Свежесть — главный фактор. Мало откликов = твоё окно.
    if project.offers == 0:
        pts += 40
    elif project.offers <= 2:
        pts += 25
    elif project.offers <= 5:
        pts += 10

    # Бюджет.
    b = project.budget
    if b >= 30000:
        pts += 20
    elif b >= 10000:
        pts += 14
    elif b >= 5000:
        pts += 8
    elif b >= 2000:
        pts += 4

    # Адекватность заказчика.
    if project.buyer_hire_rate >= 70:
        pts += 8
    elif project.buyer_hire_rate >= 40:
        pts += 4
    if project.buyer_projects >= 5:
        pts += 2

    return max(0, min(100, pts))


def evaluate(project: Project, cfg: Config) -> Project:
    """Проставляет score в проект и возвращает его же."""
    project.score = score(project, cfg)
    return project
