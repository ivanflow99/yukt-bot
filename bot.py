import logging
import re
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import gspread
from google.oauth2.service_account import Credentials

# Загружаем токен из переменных окружения для безопасности
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [5389107276, 775541480, 775541484]
SHEET_ID = "1JPsviN-x-9hHed-z3VRUalFZF-CdX0ICUoTZt6wKCw4"

PHONE_REGEX = re.compile(r'[\+7|8][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')
CHOOSE_ACTION, GET_TECHNIKA, GET_ZAPCHAST, GET_KONTAKT, CONFIRM = range(5)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTACTS = (
    "📍 г. Самара, Ракитовское шоссе, 9К, оф. 2\n"
    "📞 +7 917 012-50-02\n"
    "📞 +7 917 146-50-24\n"
    "📧 samaramaz@yandex.ru\n"
    "🕐 Работаем пн–пт, 9:00–18:00"
)

def get_sheet():
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json:
            raise Exception("GOOGLE_CREDENTIALS not set")
        creds_data = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        logger.error(f"Ошибка Google Sheets: {e}")
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
            "🆕 Новая"
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        logger.error(f"Ошибка записи: {e}")
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
        "⬇️ *Используйте кнопки внизу экрана* ⬇️",
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
            "📞 Укажите ваш номер телефона — перезвоним в рабочее время (9:00–18:00):",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return GET_KONTAKT
    await update.message.reply_text(
        "Хорошо, оформляем заявку!\n\n"
        "*Шаг 1 из 3*\n"
        "🚜 Укажите марку и модель техники:\n\n"
        "_Примеры: Komatsu PC200, Hitachi ZX200, Cat 320, Doosan DX225_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_TECHNIKA

async def get_technika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 3:
        await update.message.reply_text(
            "⚠️ Укажите подробнее.\n_Например: Komatsu PC200_",
            parse_mode="Markdown"
        )
        return GET_TECHNIKA
    context.user_data['technika'] = update.message.text.strip()
    await update.message.reply_text(
        "*Шаг 2 из 3*\n"
        "🔧 Какая запчасть нужна?\n\n"
        "_Укажите название или артикул:\nфильтр масляный, 6736-51-5141, гидронасос..._\n\n"
        "Если не знаете артикул — опишите своими словами.",
        parse_mode="Markdown"
    )
    return GET_ZAPCHAST

async def get_zapchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 2:
        await update.message.reply_text("⚠️ Опишите запчасть подробнее.")
        return GET_ZAPCHAST
    context.user_data['zapchast'] = update.message.text.strip()
    await update.message.reply_text(
        "*Шаг 3 из 3*\n"
        "📞 Укажите номер телефона для связи:\n\n"
        "Нажмите кнопку ниже 👇 или напишите номер вручную",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
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
                "⚠️ Введите номер в формате *+7 917 123-45-67*\nили нажмите кнопку 👇",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return GET_KONTAKT
        phone = raw
    context.user_data['kontakt'] = phone
    if context.user_data.get('tip') == "📞 Перезвонить мне":
        context.user_data['technika'] = '—'
        context.user_data['zapchast'] = 'Просьба перезвонить'
        return await send_zayavka(update, context)
    
    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm")],
        [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")],
    ])
    await update.message.reply_text(
        "📋 *Проверьте заявку:*\n\n"
        f"🚜 Техника: *{technika}*\n"
        f"🔧 Запчасть: *{zapchast}*\n"
        f"📞 Телефон: *{phone}*\n\n"
        "Всё верно? Нажмите кнопку ниже 👇",
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
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "без username"
    name = user.first_name or "Без имени"
    
    saved = save_to_sheet({
        "name": name,
        "username": username,
        "kontakt": kontakt,
        "tip": tip,
        "technika": technika,
        "zapchast": zapchast
    })
    
    await query.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        f"🚜 {technika}\n"
        f"🔧 {zapchast}\n"
        f"📞 {kontakt}\n\n"
        "Наш менеджер свяжется с вами в рабочее время.\n\n"
        f"По срочным вопросам:\n{CONTACTS}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    sheets_icon = "✅" if saved else "⚠️"
    notification = (
        f"🔔 *НОВАЯ ЗАЯВКА*\n\n"
        f"👤 {name} {username}\n"
        f"📞 {kontakt}\n\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n\n"
        f"{sheets_icon} Таблица: https://docs.google.com/spreadsheets/d/{SHEET_ID}"
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
        "name": name,
        "username": username,
        "kontakt": kontakt,
        "tip": "📞 Перезвонить",
        "technika": "—",
        "zapchast": "Просьба перезвонить"
    })
    await update.message.reply_text(
        "✅ *Принято!*\n\nПерезвоним в рабочее время (9:00–18:00).\n\n"
        f"По срочным вопросам:\n{CONTACTS}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    sheets_icon = "✅" if saved else "⚠️"
    notification = (
        f"🔔 *ПЕРЕЗВОНИТЬ КЛИЕНТУ*\n\n"
        f"👤 {name} {username}\n"
        f"📞 {kontakt}\n\n"
        f"{sheets_icon} Таблица: https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")
    context.user_data.clear()
    return CHOOSE_ACTION

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⬇️ Используйте кнопки внизу экрана ⬇️",
        reply_markup=main_keyboard()
    )
    return CHOOSE_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_keyboard())
    return CHOOSE_ACTION

def main():
    if not BOT_TOKEN:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения BOT_TOKEN не задана!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^(📋 Оставить заявку|📞 Перезвонить мне|📍 Контакты)$"), choose_action),
        ],
        states={
            CHOOSE_ACTION: [MessageHandler(filters.Regex("^(📋 Оставить заявку|📞 Перезвонить мне|📍 Контакты)$"), choose_action)],
            GET_TECHNIKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_technika)],
            GET_ZAPCHAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_zapchast)],
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
