import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8828982594:AAGsoCPmykGoclRCOtBHKq7WYHdl8YgTbtw"

# Chat ID кому приходят уведомления (ты, папа, брат)
ADMIN_IDS = [5389107276, 775541480, 775541484]

# ===== ЭТАПЫ ДИАЛОГА =====
TECHNIKA, ZAPCHAST, KONTAKT = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🔍 Узнать наличие")],
        [KeyboardButton("📋 Оформить заявку")],
        [KeyboardButton("💰 Узнать цену")],
        [KeyboardButton("📞 Попросить перезвонить")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Добро пожаловать в *ЮКТ Самара*!\n\n"
        "Запчасти на спецтехнику:\n"
        "🔧 Экскаваторы: Komatsu, Hitachi, Cat, Doosan\n"
        "🚜 Погрузчики и другая спецтехника\n\n"
        "📦 Склад в Самаре + доставка под заказ\n"
        "🕐 Работаем 9:00–18:00\n\n"
        "Выберите что вас интересует:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ===== Начало заявки =====
async def start_zayavka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['tip'] = text
    
    await update.message.reply_text(
        "Хорошо! Напишите *марку и модель техники*\n\n"
        "Например: _Komatsu PC200_ или _Hitachi ZX200_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return TECHNIKA

# ===== Шаг 1: техника =====
async def get_technika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['technika'] = update.message.text
    await update.message.reply_text(
        "Отлично! Теперь напишите *какая запчасть нужна*\n\n"
        "Можно артикул или описание: _фильтр масляный_, _звёздочка ведущая_ и т.д.",
        parse_mode="Markdown"
    )
    return ZAPCHAST

# ===== Шаг 2: запчасть =====
async def get_zapchast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['zapchast'] = update.message.text
    await update.message.reply_text(
        "Почти готово! Укажите *ваш номер телефона* для связи:",
        parse_mode="Markdown"
    )
    return KONTAKT

# ===== Шаг 3: контакт + отправка уведомлений =====
async def get_kontakt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    context.user_data['kontakt'] = update.message.text

    tip = context.user_data.get('tip', 'Не указано')
    technika = context.user_data.get('technika', 'Не указано')
    zapchast = context.user_data.get('zapchast', 'Не указано')
    kontakt = context.user_data.get('kontakt', 'Не указано')
    username = f"@{user.username}" if user.username else "нет username"
    name = user.first_name or "Без имени"

    # Сообщение клиенту
    keyboard = [
        [KeyboardButton("🔍 Узнать наличие")],
        [KeyboardButton("📋 Оформить заявку")],
        [KeyboardButton("💰 Узнать цену")],
        [KeyboardButton("📞 Попросить перезвонить")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ *Заявка принята!*\n\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📞 Контакт: {kontakt}\n\n"
        "Свяжемся с вами в течение часа в рабочее время (9:00–18:00).\n"
        "Если срочно — позвоните нам напрямую.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    # Уведомление администраторам
    notification = (
        f"🔔 *Новая заявка!*\n\n"
        f"👤 Клиент: {name} {username}\n"
        f"📋 Тип: {tip}\n"
        f"🚜 Техника: {technika}\n"
        f"🔧 Запчасть: {zapchast}\n"
        f"📞 Контакт: {kontakt}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление {admin_id}: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# ===== Отмена =====
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🔍 Узнать наличие")],
        [KeyboardButton("📋 Оформить заявку")],
        [KeyboardButton("💰 Узнать цену")],
        [KeyboardButton("📞 Попросить перезвонить")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Хорошо, вернулись в главное меню.",
        reply_markup=reply_markup
    )
    context.user_data.clear()
    return ConversationHandler.END

# ===== Обычное сообщение вне диалога =====
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🔍 Узнать наличие")],
        [KeyboardButton("📋 Оформить заявку")],
        [KeyboardButton("💰 Узнать цену")],
        [KeyboardButton("📞 Попросить перезвонить")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Выберите один из вариантов ниже 👇",
        reply_markup=reply_markup
    )

# ===== ЗАПУСК =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(🔍 Узнать наличие|📋 Оформить заявку|💰 Узнать цену|📞 Попросить перезвонить)$"), start_zayavka)
        ],
        states={
            TECHNIKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_technika)],
            ZAPCHAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_zapchast)],
            KONTAKT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_kontakt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
