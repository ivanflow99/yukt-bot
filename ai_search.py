"""
AI-подбор позиций из каталога ЮКТ Самара по запросу клиента.
Использует Claude API (Anthropic) для понимания запроса с учётом
синонимов, опечаток и разных формулировок марок техники.
"""

import os
import json
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

_client = None
_catalog = None


def _get_client():
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY не задан в переменных окружения")
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _load_catalog():
    global _catalog
    if _catalog is None:
        with open(CATALOG_PATH, encoding="utf-8") as f:
            _catalog = json.load(f)
    return _catalog


def _catalog_as_text(catalog):
    """Компактное текстовое представление каталога для промпта."""
    lines = [f"{c['id']}|{c['name']}|{c['price']}₽" for c in catalog]
    return "\n".join(lines)


SYSTEM_PROMPT = """Ты — помощник склада запчастей для спецтехники ЮКТ Самара \
(Komatsu, Hitachi, Caterpillar, Doosan, Hyundai).

Тебе дан каталог в формате "ID|Название|Цена". Клиент описывает технику \
и нужную запчасть своими словами — возможны опечатки, сокращения, синонимы \
(например "гидронасос" = "насос гидравлический", "ПК200" = "PC200").

Найди до 3 наиболее подходящих позиций из каталога. Если ничего подходящего \
нет — верни пустой список matches.

Отвечай ТОЛЬКО валидным JSON без markdown-разметки, в формате:
{"matches": [{"id": <int>, "reason": "<короткое объяснение совпадения, до 8 слов>"}], "note": "<опционально: краткий комментарий, если запрос неясен>"}
"""


def find_matches(technika: str, zapchast: str) -> dict:
    """
    Ищет в каталоге позиции, подходящие под запрос клиента.

    Возвращает dict:
    {
        "matches": [{"name": str, "price": int, "url": str, "reason": str}, ...],
        "note": str | None
    }
    Если API недоступен или произошла ошибка — возвращает пустой результат
    с описанием ошибки в note, не прерывая основной флоу бота.
    """
    try:
        catalog = _load_catalog()
        client = _get_client()

        user_query = f"Техника: {technika}\nНужна запчасть: {zapchast}"
        catalog_text = _catalog_as_text(catalog)

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Каталог:\n{catalog_text}\n\nЗапрос клиента:\n{user_query}",
                }
            ],
        )

        raw_text = response.content[0].text.strip()
        # на случай если модель всё же обернёт в ```json ... ```
        raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed = json.loads(raw_text)
        catalog_by_id = {c["id"]: c for c in catalog}

        matches = []
        for m in parsed.get("matches", [])[:3]:
            item = catalog_by_id.get(m.get("id"))
            if item:
                matches.append({
                    "name": item["name"],
                    "price": item["price"],
                    "url": item["url"],
                    "reason": m.get("reason", ""),
                })

        return {"matches": matches, "note": parsed.get("note")}

    except Exception as e:
        logger.error(f"Ошибка AI-поиска: {e}")
        return {"matches": [], "note": None, "error": str(e)}


def format_matches_for_admin(result: dict) -> str:
    """Форматирует результат поиска для уведомления админу."""
    matches = result.get("matches", [])
    if not matches:
        if result.get("error"):
            return "🤖 AI-подбор: недоступен (ошибка)"
        return "🤖 AI-подбор: совпадений в каталоге не найдено"

    lines = ["🤖 *AI нашёл похожие позиции в каталоге:*"]
    for m in matches:
        price_str = f"{m['price']:,}".replace(",", " ") + " ₽" if m['price'] else "цена не указана"
        lines.append(f"• {m['name']} — {price_str}\n  {m['url']}")
    if result.get("note"):
        lines.append(f"\n_{result['note']}_")
    return "\n".join(lines)
