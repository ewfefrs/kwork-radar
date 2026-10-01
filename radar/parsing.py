"""Чистая логика разбора карточек Kwork (без браузера — тестируемо)."""
from __future__ import annotations

import re

from .models import Project

BASE = "https://kwork.ru"

# JS, который вытаскивает данные карточек из отрисованного DOM.
EXTRACT_JS = r"""
() => {
  const cards = [...document.querySelectorAll('.want-card')];
  return cards.map(card => {
    const a = card.querySelector('.wants-card__header-title a');
    const descEl = card.querySelector('.wants-card__description-text');
    const priceEl = card.querySelector('.wants-card__price');
    return {
      url: a ? a.getAttribute('href') : null,
      title: a ? a.innerText.trim() : '',
      desc: descEl ? descEl.innerText.trim() : '',
      price: priceEl ? priceEl.innerText.trim() : '',
      meta: card.innerText.replace(/\s+/g, ' ').trim(),
    };
  });
}
"""


def rub_amounts(text: str) -> list[int]:
    """Достаёт суммы в рублях: '2 000 ₽', '10 000 ₽' → [2000, 10000]."""
    out = []
    for m in re.finditer(r"([\d][\d\s ]*)\s*₽", text):
        digits = re.sub(r"\D", "", m.group(1))
        if digits:
            out.append(int(digits))
    return out


def search_int(pattern: str, text: str, default: int = 0) -> int:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default


def parse_card(raw: dict) -> Project | None:
    url = raw.get("url") or ""
    m = re.search(r"/projects/(\d+)", url)
    if not m:
        return None
    pid = m.group(1)
    meta = raw.get("meta", "")

    amounts = rub_amounts(raw.get("price", "")) or rub_amounts(meta)
    if len(amounts) >= 2:
        desired, mx = amounts[0], amounts[-1]
    elif len(amounts) == 1:
        desired = mx = amounts[0]
    else:
        desired = mx = 0

    time_m = re.search(r"Осталось:\s*(.+?)(?:\s*Предложени|$)", meta)
    buyer_m = re.search(r"Покупатель:\s*([^\s]+)", meta)
    desc = re.sub(r"\s*Показать полностью\s*$", "", raw.get("desc", "")).strip()

    return Project(
        id=pid,
        url=f"{BASE}/projects/{pid}",
        title=raw.get("title", "").strip(),
        description=desc,
        budget_desired=desired,
        budget_max=mx,
        offers=search_int(r"Предложений:\s*(\d+)", meta),
        time_left=(time_m.group(1).strip() if time_m else ""),
        buyer=(buyer_m.group(1).strip() if buyer_m else ""),
        buyer_hire_rate=search_int(r"Нанято:\s*(\d+)\s*%", meta),
        buyer_projects=search_int(r"Размещено проектов на бирже:\s*(\d+)", meta),
    )
