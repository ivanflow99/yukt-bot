import logging
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8828982594:AAGsoCPmykGoclRCOtBHKq7WYHdl8YgTbtw"
ADMIN_IDS = [5389107276, 775541480, 775541484]
PHONE_REGEX = re.compile(r'[\+7|8][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')

# ===== ЭТАПЫ =====
CHOOSE_ACTION, GET_TECHNIKA, GET_ZAPCHAST, GET_KONTAKT, CONFIRM = range(5)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Проверить наличие"), KeyboardButton("📋 Оформить заявку")],
        [KeyboardButton("💰 Узнать цену"),       KeyboardButton("📞 Перезвонить мне")],
    ], resize_keyboard=True)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Добро пожаловать в *ЮКТ Самара!*\n\n"
        "Мы поставляем запчасти на спецтехнику:\n"
        "🔧 *Экскаваторы:* Komatsu, Hitachi, Cat, Doosan, Hyundai\n"
        "🚜 *Погрузчики:* все марки\n\n"
        "📦 Склад в Самаре — отгрузка день в день\n"
        "🚚 Доставка под заказ по всей России\n"
        "🕐 Работаем *9:00–18:00* (пн–пт)\n\n"
        "💬 Выберите что вас интересует:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return CHOOSE_ACTION

# ===== Выбор действия =====
async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['tip'] = text

    if text == "📞 Перезвонить мне":
        await update.message.reply_text(
            "📞 Укажите ваш *номер телефона* — перезвоним в течение часа:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Отправить мой номер", request_contact=True)]],
                resize_keyboard=True, one_time_keyboard=True
            )
        )
        return GET_KONTAKT

    prompts = {
        "🔍 Проверить наличие": "Укажите *марку и модель техники*\n\nНапример: _Komatsu PC200_ или _Hitachi ZX200_",
        "📋 Оформить заявку":   "Укажите *марку и модель техники*\n\nНапример: _Komatsu PC200_ или _Cat 320_",
        "💰 Узнать цену":       "Укажите *марку и модель техники*\n\nНапример: _Doosan DX225_ или _Hyundai R210_",
    }
    prompt = prompts.get(text, "Укажите *марку и модель техники:*")
    await update.message.reply_text(
        f"Хорошо! {prompt}",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_TECHNIKA

# ===== Техника =====
async def get_technika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 3:
        await update.message.reply_text("⚠️ Пожалуйста, укажите марку и модель подробнее.\n\nНапример: _Komatsu PC200_", parse_mode="Markdown")
        return GET_TECHNIKA
    context.user_data['technika'] = update.message.text.strip()
    await update.message.reply_text(
        "Отлично! Теперь опишите *какая запчасть нужна*\n\n"
        "Можно артикул, название или описание:\n"
        "_фильтр масляный_, _6736-51-5141_, _звёздочка ведущая_, _гидронасос_ и т.д.",
        parse_mode="Markdown"
    )
    return GET_ZAPCHAST

# ===== Запчасть =====
async def get_zapchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(update.message.text.strip()) < 2:
        await update.message.reply_text("⚠️ Опишите запчасть подробнее — название или артикул.")
        return GET_ZAPCHAST
    context.user_data['zapchast'] = update.message.text.strip()
    await update.message.reply_text(
        "Почти готово! Укажите *номер телефона* для связи:\n\n"
        "Например: _+7 927 123-45-67_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Отправить мой номер", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return GET_KONTAKT

# ===== Контакт =====
async def get_kontakt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем номер — либо через кнопку, либо вручную
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
    else:
        raw = update.message.text.strip()
        if not PHONE_REGEX.search(raw) and len(raw) < 5:
            await update.message.reply_text(
                "⚠️ Похоже это не номер телефона.\n\n"
                "Введите номер в формате *+7 927 123-45-67* или нажмите кнопку ниже:",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Отправить мой номер", request_contact=True)]],
                    resize_keyboard=True, one_time_keyboard=True
                )
            )
            return GET_KONTAKT
        phone = raw

    context.user_data['kontakt'] = phone

    # Если это звонок — сразу финализируем
    if context.user_data.get('tip') == "📞 Перезвонить мне":
        context.user_data['technika'] = '—'
        context.user_data['zapchast'] = 'Просьба перезвонить'
        return await finalize(update, context)

    # Показываем подтверждение
    tip = context.user_data.get('tip', '')
    technika = context.user_data.get('technika', '')
    zapchast = context.user_data.get('zapchast', '')

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить заявку", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Изменить", callback_data="edit")],
    ])
    await update.message.reply_text(
        f"📋 *Проверьте заявку:*\n\n"
        f"📌 Тип: {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
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

    if query.data == "edit":
        await query.message.reply_text(
            "Хорошо, начнём заново. Выберите действие:",
            reply_markup=main_keyboard()
        )
        context.user_data.clear()
        return CHOOSE_ACTION

    return await finalize_callback(update, context)

async def finalize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    tip = context.user_data.get('tip', '—')
    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "нет username"
    name = user.first_name or "Без имени"

    await query.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📞 Телефон: {kontakt}\n\n"
        "Свяжемся с вами в течение часа в рабочее время.\n"
        "Для срочных вопросов позвоните нам напрямую.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    notification = (
        f"🔔 *Новая заявка!*\n\n"
        f"👤 {name} {username}\n"
        f"📋 {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📞 Телефон: {kontakt}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await query.get_bot().send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка уведомления {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

async def finalize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    tip = context.user_data.get('tip', '—')
    technika = context.user_data.get('technika', '—')
    zapchast = context.user_data.get('zapchast', '—')
    kontakt = context.user_data.get('kontakt', '—')
    username = f"@{user.username}" if user.username else "нет username"
    name = user.first_name or "Без имени"

    await update.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        f"📞 Телефон: {kontakt}\n\n"
        "Перезвоним в течение часа в рабочее время (9:00–18:00).",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    notification = (
        f"🔔 *Новая заявка!*\n\n"
        f"👤 {name} {username}\n"
        f"📋 {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📞 Телефон: {kontakt}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=notification, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка уведомления {admin_id}: {e}")

    context.user_data.clear()
    return CHOOSE_ACTION

# ===== Неизвестное сообщение =====
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите один из вариантов 👇",
        reply_markup=main_keyboard()
    )
    return CHOOSE_ACTION

# ===== /cancel =====
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
            MessageHandler(filters.Regex("^(🔍 Проверить наличие|📋 Оформить заявку|💰 Узнать цену|📞 Перезвонить мне)$"), choose_action),
        ],
        states={
            CHOOSE_ACTION: [MessageHandler(filters.Regex("^(🔍 Проверить наличие|📋 Оформить заявку|💰 Узнать цену|📞 Перезвонить мне)$"), choose_action)],
            GET_TECHNIKA:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_technika)],
            GET_ZAPCHAST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_zapchast)],
            GET_KONTAKT:   [
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
