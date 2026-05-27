import logging
import re
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import gspread
from google.oauth2.service_account import Credentials

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8828982594:AAGsoCPmykGoclRCOtBHKq7WYHdl8YgTbtw"
ADMIN_IDS = [5389107276, 775541480, 775541484]
SHEET_ID = "1JPsviN-x-9hHed-z3VRUalFZF-CdX0ICUoTZt6wKCw4"
PHONE_REGEX = re.compile(r'[\+7|8][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')

CHOOSE_ACTION, GET_TECHNIKA, GET_ZAPCHAST, GET_KOLICHESTVO, GET_KONTAKT, CONFIRM = range(6)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTACTS = (
    "📍 г. Самара, Ракитовское шоссе, 9К, оф. 2\n"
    "📞 +7 917 012-50-02\n"
    "📞 +7 917 146-50-24\n"
    "📧 samaramaz@yandex.ru\n"
    "🕐 Работаем пн–пт, 9:00–18:00"
)

# ===== GOOGLE SHEETS =====
def get_sheet():
    try:
        import os
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json:
            raise Exception("GOOGLE_CREDENTIALS not set")
        creds_data = json.loads(creds_json)
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def save_to_sheet(data: dict):
    try:
        sheet = get_sheet()
        if not sheet:
            return False
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        row = [
            now,
            data.get("name", "—"),
            data.get("username", "—"),
            data.get("kontakt", "—"),
            data.get("tip", "—"),
            data.get("technika", "—"),
            data.get("zapchast", "—"),
            data.get("kolichestvo", "—"),
            "Новая"
        ]
        sheet.append_row(row)
        logger.info("Заявка записана в Google Sheets")
        return True
    except Exception as e:
        logger.error(f"Ошибка записи в Sheets: {e}")
        return False

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 Оставить заявку")],
        [KeyboardButton("📞 Перезвонить мне"), KeyboardButton("📍 Контакты")],
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Добро пожаловать в *ЮКТ Самара!*\n\n"
        "Поставляем запчасти на спецтехнику:\n"
        "🔧 Экскаваторы — Komatsu, Hitachi, Cat, Doosan, Hyundai\n"
        "🚜 Погрузчики и другая спецтехника\n\n"
        "📦 Склад в Самаре — отгрузка день в день\n"
        "🚚 Доставка по всей России\n\n"
        "👇 Выберите действие:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return CHOOSE_ACTION

async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['tip'] = text

    if text == "📍 Контакты":
        await update.message.reply_text(
            f"*ЮКТ Самара — запчасти на спецтехнику*\n\n{CONTACTS}",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        return CHOOSE_ACTION

    if text == "📞 Перезвонить мне":
        await update.message.reply_text(
            "📞 Укажите ваш номер телефона — перезвоним в рабочее время:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                resize_keyboard=True, one_time_keyboard=True
            )
        )
        return GET_KONTAKT

    await update.message.reply_text(
        "Хорошо! Оформим заявку.\n\n"
        "*Шаг 1 из 3* — укажите марку и модель техники:\n\n"
        "Например: _Komatsu PC200_, _Hitachi ZX200_, _Cat 320_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_TECHNIKA

async def get_technika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 3:
        await update.message.reply_text("⚠️ Укажите марку и модель подробнее.\n\nНапример: _Komatsu PC200_", parse_mode="Markdown")
        return GET_TECHNIKA
    context.user_data['technika'] = update.message.text.strip()
    await update.message.reply_text(
        "*Шаг 2 из 3* — какая запчасть нужна?\n\n"
        "Укажите название, артикул или описание:\n"
        "_фильтр масляный_, _6736-51-5141_, _гидронасос_, _звёздочка ведущая_",
        parse_mode="Markdown"
    )
    return GET_ZAPCHAST

async def get_zapchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 2:
        await update.message.reply_text("⚠️ Опишите запчасть подробнее — название или артикул.")
        return GET_ZAPCHAST
    context.user_data['zapchast'] = update.message.text.strip()
    await update.message.reply_text(
        "*Шаг 3 из 3* — сколько штук нужно?\n\nУкажите количество или напишите _не знаю_",
        parse_mode="Markdown"
    )
    return GET_KOLICHESTVO

async def get_kolichestvo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kolichestvo'] = update.message.text.strip()
    await update.message.reply_text(
        "Отлично! Укажите *номер телефона* для связи:\n\nИли нажмите кнопку 👇",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return GET_KONTAKT

async def get_kontakt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
    else:
        raw = update.message.text.strip()
        if not PHONE_REGEX.search(raw) and len(raw) < 6:
            await update.message.reply_text(
                "⚠️ Укажите номер в формате *+7 917 123-45-67*\nили нажмите кнопку 👇",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                    resize_keyboard=True, one_time_keyboard=True
                )
            )
            return GET_KONTAKT
        phone = raw

    context.user_data['kontakt'] = phone

    if context.user_data.get('tip') == "📞 Перезвонить мне":
        context.user_data['technika'] = '—'
        context.user_data['zapchast'] = 'Просьба перезвонить'
        context.user_data['kolichestvo'] = '—'
        return await send_zayavka(update, context)

    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    kolichestvo = context.user_data.get('kolichestvo', '—')

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Начать заново", callback_data="restart")],
    ])
    await update.message.reply_text(
        "📋 *Проверьте заявку:*\n\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📦 Количество: {kolichestvo}\n"
        f"📞 Телефон: {phone}\n\n"
        "Всё верно?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CONFIRM

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "restart":
        await query.message.reply_text("Хорошо, начнём заново 👇", reply_markup=main_keyboard())
        context.user_data.clear()
        return CHOOSE_ACTION

    user = query.from_user
    tip = context.user_data.get('tip', '—')
    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    kolichestvo = context.user_data.get('kolichestvo', '—')
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "без username"
    name = user.first_name or "Без имени"

    # Сохраняем в Google Sheets
    saved = save_to_sheet({
        "name": name, "username": username, "kontakt": kontakt,
        "tip": tip, "technika": technika, "zapchast": zapchast, "kolichestvo": kolichestvo
    })

    await query.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        f"🚜 {technika}\n"
        f"🔧 {zapchast}\n"
        f"📦 Количество: {kolichestvo}\n\n"
        "Наш менеджер свяжется с вами в рабочее время (9:00–18:00).\n\n"
        f"По срочным вопросам:\n{CONTACTS}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    sheets_status = "✅ Записано в таблицу" if saved else "⚠️ Ошибка записи в таблицу"
    notification = (
        f"🔔 *Новая заявка!*\n\n"
        f"👤 {name} {username}\n"
        f"📋 {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📦 Количество: {kolichestvo}\n"
        f"📞 Телефон: {kontakt}\n\n"
        f"{sheets_status}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await query.get_bot().send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

async def send_zayavka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "без username"
    name = user.first_name or "Без имени"

    saved = save_to_sheet({
        "name": name, "username": username, "kontakt": kontakt,
        "tip": "📞 Перезвонить", "technika": "—", "zapchast": "Просьба перезвонить", "kolichestvo": "—"
    })

    await update.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        "Перезвоним в рабочее время (9:00–18:00).\n\n"
        f"По срочным вопросам:\n{CONTACTS}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    sheets_status = "✅ Записано в таблицу" if saved else "⚠️ Ошибка записи в таблицу"
    notification = (
        f"🔔 *Новая заявка — перезвонить!*\n\n"
        f"👤 {name} {username}\n"
        f"📞 Телефон: {kontakt}\n\n"
        f"{sheets_status}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👇 Выберите действие:", reply_markup=main_keyboard())
    return CHOOSE_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено. Выберите действие:", reply_markup=main_keyboard())
    return CHOOSE_ACTION

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^(📋 Оставить заявку|📞 Перезвонить мне|📍 Контакты)$"), choose_action),
        ],
        states={
            CHOOSE_ACTION:   [MessageHandler(filters.Regex("^(📋 Оставить заявку|📞 Перезвонить мне|📍 Контакты)$"), choose_action)],
            GET_TECHNIKA:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_technika)],
            GET_ZAPCHAST:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_zapchast)],
            GET_KOLICHESTVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_kolichestvo)],
            GET_KONTAKT: [
                MessageHandler(filters.CONTACT, get_kontakt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_kontakt),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    logger.info("Бот ЮКТ Самара запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
