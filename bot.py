import logging
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8828982594:AAGsoCPmykGoclRCOtBHKq7WYHdl8YgTbtw"
ADMIN_IDS = [5389107276, 775541480, 775541484]
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

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📋 Оставить заявку")],
        [KeyboardButton("📞 Перезвонить мне"), KeyboardButton("📍 Контакты")],
    ], resize_keyboard=True)

# ===== /start =====
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

# ===== Выбор действия =====
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

    # Оставить заявку
    await update.message.reply_text(
        "Хорошо! Давайте оформим заявку.\n\n"
        "Шаг 1 из 3 — укажите *марку и модель техники:*\n\n"
        "Например: _Komatsu PC200_, _Hitachi ZX200_, _Cat 320_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_TECHNIKA

# ===== Шаг 1: Техника =====
async def get_technika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 3:
        await update.message.reply_text(
            "⚠️ Укажите марку и модель подробнее.\n\nНапример: _Komatsu PC200_",
            parse_mode="Markdown"
        )
        return GET_TECHNIKA
    context.user_data['technika'] = update.message.text.strip()
    await update.message.reply_text(
        "Шаг 2 из 3 — *какая запчасть нужна?*\n\n"
        "Укажите название, артикул или описание:\n"
        "_фильтр масляный_, _6736-51-5141_, _звёздочка ведущая_, _гидронасос_",
        parse_mode="Markdown"
    )
    return GET_ZAPCHAST

# ===== Шаг 2: Запчасть =====
async def get_zapchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 2:
        await update.message.reply_text("⚠️ Опишите запчасть подробнее — название или артикул.")
        return GET_ZAPCHAST
    context.user_data['zapchast'] = update.message.text.strip()
    await update.message.reply_text(
        "Шаг 3 из 3 — *сколько штук нужно?*\n\n"
        "Укажите количество или напишите _не знаю_",
        parse_mode="Markdown"
    )
    return GET_KOLICHESTVO

# ===== Шаг 3: Количество =====
async def get_kolichestvo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kolichestvo'] = update.message.text.strip()
    await update.message.reply_text(
        "Отлично! Последний шаг — *ваш номер телефона:*\n\n"
        "Или нажмите кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return GET_KONTAKT

# ===== Контакт =====
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

    # Если звонок — без подтверждения
    if context.user_data.get('tip') == "📞 Перезвонить мне":
        context.user_data['technika'] = '—'
        context.user_data['zapchast'] = 'Просьба перезвонить'
        context.user_data['kolichestvo'] = '—'
        return await send_zayavka(update, context)

    # Подтверждение заявки
    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    kolichestvo = context.user_data.get('kolichestvo', '—')

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Начать заново", callback_data="restart")],
    ])
    await update.message.reply_text(
        "📋 *Проверьте заявку перед отправкой:*\n\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📦 Количество: {kolichestvo}\n"
        f"📞 Телефон: {phone}\n\n"
        "Всё верно?",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return CONFIRM

# ===== Подтверждение =====
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

    # Клиенту
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

    # Нам
    notification = (
        f"🔔 *Новая заявка!*\n\n"
        f"👤 {name} {username}\n"
        f"📋 {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📦 Количество: {kolichestvo}\n"
        f"📞 Телефон: {kontakt}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await query.get_bot().send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

# ===== Отправка заявки (для звонка) =====
async def send_zayavka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "без username"
    name = user.first_name or "Без имени"

    await update.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        "Перезвоним вам в рабочее время (9:00–18:00).\n\n"
        f"По срочным вопросам:\n{CONTACTS}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    notification = (
        f"🔔 *Новая заявка — перезвонить!*\n\n"
        f"👤 {name} {username}\n"
        f"📞 Телефон: {kontakt}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

# ===== Неизвестное =====
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👇 Выберите действие:", reply_markup=main_keyboard())
    return CHOOSE_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено. Выберите действие:", reply_markup=main_keyboard())
    return CHOOSE_ACTION

# ===== ЗАПУСК =====
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
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    logger.info("Бот ЮКТ Самара запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
