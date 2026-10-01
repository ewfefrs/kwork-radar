"""Точка входа: python -m radar [--dry-run] [--once]"""
from __future__ import annotations

import argparse
import asyncio
import sys

for _stream in (sys.stdout, sys.stderr):  # кириллица/эмодзи в Windows-консоли
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Kwork Radar")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Проверить парсинг: печатает найденные заказы в консоль, без Telegram.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Сделать один проход и выйти (без бесконечного цикла).",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(dry_run=args.dry_run, once=args.once))
    except KeyboardInterrupt:
        print("\nОстановлено.")


if __name__ == "__main__":
    main()
