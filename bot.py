import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from app.config import settings

async def main():
    cfg = settings()
    if not cfg.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")
    bot = Bot(cfg.bot_token)
    dp = Dispatcher()
    launch = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🚚 Открыть CargoLink", web_app=WebAppInfo(url=cfg.webapp_url))]],
        resize_keyboard=True
    )
    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer(
            "🚚 Добро пожаловать в CargoLink!\n\n"
            "Откройте приложение, чтобы искать грузы, размещать заявки и пользоваться сервисами.",
            reply_markup=launch
        )
    @dp.message()
    async def fallback(message: Message):
        await message.answer("Откройте CargoLink кнопкой ниже.", reply_markup=launch)
    logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
