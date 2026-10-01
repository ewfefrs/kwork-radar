"""Модель заказа Kwork."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Project:
    id: str                    # id заказа (из ссылки /projects/<id>)
    url: str                   # полная ссылка на заказ
    title: str
    description: str
    budget_desired: int        # желаемый бюджет, ₽ (0 если не распознан)
    budget_max: int            # допустимый бюджет, ₽ (0 если не распознан)
    offers: int                # сколько откликов уже есть
    time_left: str             # «Осталось: 23 ч. 59 мин.»
    buyer: str                 # ник заказчика
    buyer_hire_rate: int       # % найма заказчика (0 если нет данных)
    buyer_projects: int        # сколько проектов заказчик разместил
    score: int = 0             # заполняется матчером
    kind: str = "other"        # тип заказа для шаблона (заполняется драфтером)

    @property
    def budget(self) -> int:
        """Потолок бюджета для фильтрации/сортировки."""
        return max(self.budget_max, self.budget_desired)
