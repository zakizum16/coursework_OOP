"""
Модуль обработчиков для Telegram бота
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from etu_api import api_client  # Импортируем API клиент

logger = logging.getLogger(__name__)

BOT_NAME = "ЛЭТИ Бот"
DEVELOPER_ID = 662272545

# Словарь для хранения выбранных групп пользователей
user_groups = {}


def get_beautiful_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📅 Расписание")],
            [KeyboardButton("⏱ Ближайшая пара"), KeyboardButton("🌅 Завтра")],
            [KeyboardButton("🗓 Неделя"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🔧 Сменить группу")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} (@{user.username}) sent /start")

    # Проверяем, есть ли у пользователя сохраненная группа
    if user.id not in user_groups:
        await ask_for_group(update, context)
        return

    welcome_text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Ваша группа: <b>{user_groups[user.id]}</b>\n\n"
        "Выберите действие в меню ниже:"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )

    logger.info(f"Sent welcome to {user.id}")


async def ask_for_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает номер группы у пользователя"""
    await update.message.reply_text(
        "🔢 <b>Введите номер вашей группы:</b>\n"
        "Например: <code>4353</code>, <code>2702</code>, <code>5495</code>",
        parse_mode="HTML"
    )
    # Устанавливаем состояние ожидания группы
    if context.user_data is not None:
        context.user_data['awaiting_group'] = True


async def handle_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод номера группы"""
    user = update.effective_user
    group_number = update.message.text.strip()

    logger.info(f"User {user.id} ввел группу: {group_number}")

    # Проверяем существование группы
    group_info = api_client.find_group_info(group_number)

    if not group_info:
        await update.message.reply_text(
            f"❌ Группа <b>{group_number}</b> не найдена.\n"
            "Пожалуйста, проверьте номер и попробуйте еще раз.",
            parse_mode="HTML"
        )
        return

    # Сохраняем группу пользователя
    user_groups[user.id] = group_number

    # Сбрасываем состояние ожидания
    if context.user_data is not None:
        context.user_data['awaiting_group'] = False

    await update.message.reply_text(
        f"✅ Группа <b>{group_number}</b> сохранена!\n"
        f"📋 Факультет: {group_info['faculty']}\n"
        f"🎓 Курс: {group_info['course']}\n\n"
        "Теперь вы можете использовать все функции бота!",
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок"""
    user = update.effective_user
    text = update.message.text

    logger.info(f"User {user.id} pressed: {text}")

    # Проверяем, есть ли у пользователя группа
    if user.id not in user_groups:
        await ask_for_group(update, context)
        return

    group_number = user_groups[user.id]

    if text == "📅 Расписание":
        await show_schedule_options(update, context, group_number)

    elif text == "⏱ Ближайшая пара":
        await show_next_lesson(update, context, group_number)

    elif text == "🌅 Завтра":
        await show_tomorrow_schedule(update, context, group_number)

    elif text == "🗓 Неделя":
        await show_week_schedule(update, context, group_number)

    elif text == "❓ Помощь":
        await help_command(update, context)

    elif text == "🔧 Сменить группу":
        await ask_for_group(update, context)


async def show_schedule_options(update: Update, context: ContextTypes.DEFAULT_TYPE, group_number: str):
    """Показывает варианты расписания"""
    keyboard = [
        [KeyboardButton("📅 Сегодня"), KeyboardButton("🌅 Завтра")],
        [KeyboardButton("🗓 Неделя"), KeyboardButton("⏱ Ближайшая пара")],
        [KeyboardButton("⬅️ Назад")]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"📊 <b>Расписание группы {group_number}</b>\n"
        "Выберите период:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def show_next_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, group_number: str):
    """Показывает ближайшую пару"""
    await update.message.reply_chat_action(action="typing")

    next_lesson = api_client.get_next_lesson(group_number)

    if not next_lesson:
        await update.message.reply_text(
            "❌ Не удалось загрузить расписание. Попробуйте позже.",
            reply_markup=get_beautiful_keyboard()
        )
        return

    await update.message.reply_text(
        next_lesson,
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )


async def show_tomorrow_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, group_number: str):
    """Показывает расписание на завтра"""
    await update.message.reply_chat_action(action="typing")

    tomorrow_schedule = api_client.get_tomorrow_schedule(group_number)

    if not tomorrow_schedule:
        await update.message.reply_text(
            "❌ Не удалось загрузить расписание. Попробуйте позже.",
            reply_markup=get_beautiful_keyboard()
        )
        return

    # Разбиваем длинное сообщение если нужно
    if len(tomorrow_schedule) > 4000:
        parts = [tomorrow_schedule[i:i + 4000] for i in range(0, len(tomorrow_schedule), 4000)]
        for part in parts:
            await update.message.reply_text(
                part,
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(
            tomorrow_schedule,
            reply_markup=get_beautiful_keyboard(),
            parse_mode="HTML"
        )


async def show_week_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, group_number: str):
    """Показывает расписание на неделю"""
    await update.message.reply_chat_action(action="typing")

    week_schedule = api_client.get_week_schedule(group_number)

    if not week_schedule:
        await update.message.reply_text(
            "❌ Не удалось загрузить расписание. Попробуйте позже.",
            reply_markup=get_beautiful_keyboard()
        )
        return

    # Отправляем каждый день отдельным сообщением
    for day_schedule in week_schedule:
        if len(day_schedule) > 4000:
            parts = [day_schedule[i:i + 4000] for i in range(0, len(day_schedule), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode="HTML")
        else:
            await update.message.reply_text(day_schedule, parse_mode="HTML")

    await update.message.reply_text(
        "📊 <b>Расписание на неделю загружено!</b>",
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested help")

    help_text = (
        "🆘 <b>Помощь по использованию бота</b>\n\n"
        "<b>Основные функции:</b>\n"
        "• 📅 Расписание — полное расписание занятий\n"
        "• ⏱ Ближайшая пара — следующая пара сегодня\n"
        "• 🌅 Завтра — расписание на следующий день\n"
        "• 🗓 Неделя — расписание на всю неделю\n\n"
        "<b>Команды:</b>\n"
        "/start — начать работу с ботом\n"
        "/help — показать эту справку\n"
        "/menu — показать главное меню\n"
        "/myid — показать ваш Telegram ID\n\n"
        "<b>Работа с расписанием:</b>\n"
        "1. При первом запуске введите номер группы\n"
        "2. Выберите нужную функцию в меню\n"
        "3. Для смены группы нажмите '🔧 Сменить группу'\n\n"
        "<i>Данные загружаются из официального API ЛЭТИ</i>"
    )

    await update.message.reply_text(
        help_text,
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested menu")
    await start_command(update, context)


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested their ID")

    await update.message.reply_text(
        f"👤 <b>Ваш Telegram ID:</b> <code>{user.id}</code>\n"
        f"📛 <b>Имя пользователя:</b> @{user.username}\n"
        f"👋 <b>Имя:</b> {user.first_name}",
        reply_markup=get_beautiful_keyboard(),
        parse_mode="HTML"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    error = context.error

    # Логируем ошибку
    logger.error(f"Ошибка при обработке сообщения: {error}")

    # Отправляем уведомление разработчику
    try:
        await context.bot.send_message(
            chat_id=DEVELOPER_ID,
            text=f"⚠️ <b>Ошибка в боте:</b>\n<code>{error}</code>",
            parse_mode="HTML"
        )
        logger.info("Уведомление отправлено разработчику")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление разработчику: {e}")

    # Уведомляем пользователя
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке запроса.\n"
                "Пожалуйста, попробуйте еще раз.",
                reply_markup=get_beautiful_keyboard()
            )
        except:
            pass


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    text = update.message.text

    if context.user_data is not None and context.user_data.get('awaiting_group', False):
        await handle_group_input(update, context)
        return

    await handle_buttons(update, context)