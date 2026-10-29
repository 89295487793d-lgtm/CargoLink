import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import User

settings = get_settings()
dp = Dispatcher()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚚 Найти груз"), KeyboardButton(text="📦 Разместить заявку")],
        [KeyboardButton(text="🚛 Свободные автомобили"), KeyboardButton(text="👤 Мой профиль")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите раздел CargoLink",
)
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
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=message.from_user.id, telegram_username=message.from_user.username)
            session.add(user)
            await session.commit()
        if not user.full_name:
            await message.answer("Добро пожаловать в CargoLink!\n\nНапишите имя и фамилию.")
            return
    if settings.webapp_url.startswith("https://"):
        menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚚 Открыть CargoLink", web_app=WebAppInfo(url=settings.webapp_url))],
                [KeyboardButton(text="🚚 Найти груз"), KeyboardButton(text="📦 Разместить заявку")],
                [KeyboardButton(text="🚛 Свободные автомобили"), KeyboardButton(text="👤 Мой профиль")],
            ], resize_keyboard=True
        )
        await message.answer("С возвращением в CargoLink. Выберите раздел:", reply_markup=menu)
    else:
        await message.answer("Добро пожаловать в CargoLink!\nMini App подключим после публикации по HTTPS.", reply_markup=MAIN_MENU)

@dp.message(F.contact)
async def save_contact(message: Message) -> None:
    if not message.from_user or not message.contact:
        return
    if message.contact.user_id != message.from_user.id:
        await message.answer("Отправьте именно свой номер кнопкой ниже.", reply_markup=CONTACT_MENU)
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=message.from_user.id, telegram_username=message.from_user.username)
            session.add(user)
        user.phone = message.contact.phone_number
        await session.commit()
    await message.answer("Номер сохранён приватно и не публикуется в заявках.", reply_markup=MAIN_MENU)

@dp.message(F.text)
async def text_router(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    text = message.text.strip()
    if text in {"🚚 Найти груз", "📦 Разместить заявку", "🚛 Свободные автомобили", "👤 Мой профиль"}:
        if text == "👤 Мой профиль":
            async with SessionLocal() as session:
                result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
                user = result.scalar_one_or_none()
            if user is None:
                await message.answer("Сначала отправьте /start.")
            else:
                await message.answer(f"👤 Мой профиль\nИмя: {user.full_name or 'не указано'}\nТелефон: {'указан' if user.phone else 'не указан'} (приватно)")
            return
        await message.answer(f"Раздел «{text}» подключим следующим этапом.", reply_markup=MAIN_MENU)
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user and not user.full_name and len(text) >= 3 and not text.startswith("/"):
            user.full_name = text[:200]
            user.telegram_username = message.from_user.username
            await session.commit()
            await message.answer("Спасибо! Теперь отправьте свой номер кнопкой ниже.", reply_markup=CONTACT_MENU)
            return
    await message.answer("Откройте CargoLink кнопками меню ниже.", reply_markup=MAIN_MENU)

async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан. Создайте .env на основе .env.example.")
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    bot = Bot(token=settings.bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
