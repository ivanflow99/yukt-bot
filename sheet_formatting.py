"""
Настройка внешнего вида Google Sheets для заявок ЮКТ Самара.

Запускается один раз (или при каждом старте бота — операции идемпотентны)
чтобы привести таблицу в порядок: заголовки, ширина колонок,
условное форматирование статусов, закреплённая строка заголовков.
"""

import logging
from gspread_formatting import (
    CellFormat, Color, TextFormat, format_cell_range,
    set_frozen, set_column_width,
    ConditionalFormatRule, BooleanCondition, GridRange,
    get_conditional_format_rules,
)

logger = logging.getLogger(__name__)

HEADERS = [
    "Дата/время",
    "Имя",
    "Username",
    "Телефон",
    "Тип заявки",
    "Техника",
    "Запчасть",
    "Статус",
    "AI-подбор",
]

STATUS_COLORS = {
    "🆕 Новая": Color(1, 0.95, 0.6),       # жёлтый
    "🔄 В работе": Color(0.7, 0.85, 1),     # голубой
    "✅ Закрыта": Color(0.75, 0.95, 0.75),  # зелёный
    "❌ Отмена": Color(0.95, 0.75, 0.75),   # красный
}


def setup_sheet_appearance(sheet):
    """
    Приводит таблицу в порядок: заголовки, форматирование, ширина колонок.
    Безопасно вызывать многократно — идемпотентно.
    """
    try:
        _ensure_headers(sheet)
        _format_headers(sheet)
        _set_column_widths(sheet)
        _apply_status_conditional_formatting(sheet)
        set_frozen(sheet, rows=1)
        logger.info("Оформление таблицы применено")
    except Exception as e:
        logger.error(f"Ошибка оформления таблицы: {e}")


def _ensure_headers(sheet):
    """Если первая строка не совпадает с заголовками — записывает их."""
    first_row = sheet.row_values(1)
    if first_row != HEADERS:
        sheet.update("A1", [HEADERS])


def _format_headers(sheet):
    fmt = CellFormat(
        backgroundColor=Color(0.2, 0.2, 0.25),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
        horizontalAlignment="CENTER",
    )
    format_cell_range(sheet, f"A1:{_col_letter(len(HEADERS))}1", fmt)


def _set_column_widths(sheet):
    widths = {
        "A": 130,  # Дата/время
        "B": 120,  # Имя
        "C": 120,  # Username
        "D": 130,  # Телефон
        "E": 130,  # Тип заявки
        "F": 160,  # Техника
        "G": 220,  # Запчасть
        "H": 110,  # Статус
        "I": 350,  # AI-подбор
    }
    for col, width in widths.items():
        set_column_width(sheet, col, width)


def _apply_status_conditional_formatting(sheet):
    """Цветная подсветка колонки 'Статус' по значению."""
    status_col = HEADERS.index("Статус")  # 0-indexed
    col_letter = _col_letter(status_col + 1)
    grid_range = GridRange(
        sheetId=sheet.id,
        startRowIndex=1,  # пропускаем заголовок
        startColumnIndex=status_col,
        endColumnIndex=status_col + 1,
    )

    rules = get_conditional_format_rules(sheet)
    # убираем старые правила для этой колонки, чтобы не дублировать
    rules.clear()

    for status_text, color in STATUS_COLORS.items():
        rule = ConditionalFormatRule(
            ranges=[grid_range],
            booleanRule=BooleanCondition("TEXT_EQ", [status_text]),
        )
        # gspread_formatting BooleanCondition rule needs format attached separately
        rule.booleanRule.format = CellFormat(backgroundColor=color)
        rules.append(rule)

    rules.save()


def _col_letter(n: int) -> str:
    """1 -> A, 2 -> B, ... 27 -> AA"""
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters
