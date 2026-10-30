import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
from sqlalchemy import select, text

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import User

settings = get_settings()
dp = Dispatcher()
logger = logging.getLogger("cargolink.bot")


def main_menu() -> ReplyKeyboardMarkup:
    rows = []
    if settings.webapp_url.startswith("https://"):
        rows.append([KeyboardButton(
            text="🚚 Открыть CargoLink",
            web_app=WebAppInfo(url=settings.webapp_url),
        )])
    rows.extend([
        [KeyboardButton(text="🚚 Найти груз"), KeyboardButton(text="📦 Разместить заявку")],
        [KeyboardButton(text="🚛 Свободные автомобили"), KeyboardButton(text="👤 Мой профиль")],
    ])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел CargoLink",
    )


MAIN_MENU = main_menu()
CONTACT_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


@dp.message(CommandStart())
async def start(message: Message) -> None:
    if not message.from_user:
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                telegram_username=message.from_user.username,
            )
            session.add(user)
            await session.commit()

        registered = bool(user.full_name)

    if not registered:
        await message.answer(
            "Добро пожаловать в CargoLink!\n\n"
            "Для регистрации напишите имя и фамилию."
        )
        return

    await message.answer(
        "С возвращением в CargoLink. Выберите раздел:",
        reply_markup=MAIN_MENU,
    )


@dp.message(F.contact)
async def save_contact(message: Message) -> None:
    if not message.from_user or not message.contact:
        return

    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "Отправьте именно свой номер кнопкой ниже.",
            reply_markup=CONTACT_MENU,
        )
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                telegram_username=message.from_user.username,
            )
            session.add(user)
        user.phone = message.contact.phone_number
        await session.commit()

    await message.answer(
        "Номер сохранён в профиле и не публикуется в заявках.",
        reply_markup=MAIN_MENU,
    )


@dp.message(F.text)
async def text_router(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    incoming = message.text.strip()
    menu_items = {
        "🚚 Найти груз",
        "📦 Разместить заявку",
        "🚛 Свободные автомобили",
        "👤 Мой профиль",
    }

    if incoming == "👤 Мой профиль":
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()

        if user is None:
            await message.answer("Сначала отправьте /start.")
        else:
            await message.answer(
                "👤 Мой профиль\n"
                f"Имя: {user.full_name or 'не указано'}\n"
                f"Телефон: {'указан' if user.phone else 'не указан'} (приватно)",
                reply_markup=MAIN_MENU,
            )
        return

    if incoming in menu_items:
        await message.answer(
            f"Раздел «{incoming}» будет подключён следующим этапом.",
            reply_markup=MAIN_MENU,
        )
        return

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            await message.answer("Для начала регистрации отправьте /start.")
            return

        if not user.full_name and len(incoming) >= 3 and not incoming.startswith("/"):
            user.full_name = incoming[:200]
            user.telegram_username = message.from_user.username
            await session.commit()
            await message.answer(
                "Спасибо! Теперь отправьте свой номер кнопкой ниже.",
                reply_markup=CONTACT_MENU,
            )
            return

    await message.answer(
        "Выберите действие с помощью кнопок меню.",
        reply_markup=MAIN_MENU,
    )


async def main() -> None:
    token = settings.bot_token.strip()
    if not token or token == "PASTE_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError(
            "Не задан BOT_TOKEN. Создайте Telegram-бота через @BotFather "
            "и добавьте токен в переменные окружения или файл .env."
        )

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(token=token)
    try:
        # Fail early with a clear message if PostgreSQL is unavailable.
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        # This project uses long polling; remove a stale webhook without
        # discarding updates waiting in Telegram.
        await bot.delete_webhook(drop_pending_updates=False)
        bot_info = await bot.get_me()
        logger.info("CargoLink bot started: @%s (id=%s)", bot_info.username, bot_info.id)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("CargoLink bot stopped")
