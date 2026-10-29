import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from config import settings

async def main():
    cfg=settings()
    if not cfg.bot_token: raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")
    bot=Bot(token=cfg.bot_token); dp=Dispatcher()
    menu=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🚚 Открыть CargoLink",web_app=WebAppInfo(url=cfg.webapp_url))]],resize_keyboard=True)
    @dp.message(CommandStart())
    async def start(message:Message):
        await message.answer("🚚 Добро пожаловать в CargoLink!\n\nОткройте приложение кнопкой ниже.",reply_markup=menu)
    @dp.message()
    async def fallback(message:Message):
        await message.answer("Откройте CargoLink кнопкой ниже.",reply_markup=menu)
    logging.basicConfig(level=getattr(logging,cfg.log_level,logging.INFO))
    try: await dp.start_polling(bot)
    finally: await bot.session.close()
if __name__=="__main__": asyncio.run(main())
