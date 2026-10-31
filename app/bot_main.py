import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from sqlalchemy import select, text

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import CargoRequest, User

settings = get_settings()
dp = Dispatcher()
logger = logging.getLogger("cargolink.bot")


class PlacementForm(StatesGroup):
    origin = State()
    destination = State()
    cargo = State()
    weight = State()
    vehicle = State()
    pickup_date = State()
    price = State()
    confirm = State()


def main_menu() -> ReplyKeyboardMarkup:
    rows = []
    if settings.webapp_url.startswith("https://"):
        rows.append([KeyboardButton(text="🚚 Открыть CargoLink", web_app=WebAppInfo(url=settings.webapp_url))])
    rows.extend([
        [KeyboardButton(text="🚚 Найти груз"), KeyboardButton(text="📦 Разместить заявку")],
        [KeyboardButton(text="🚛 Свободные автомобили"), KeyboardButton(text="👤 Мой профиль")],
    ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Выберите раздел CargoLink")


MAIN_MENU = main_menu()
CONTACT_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
CONFIRM_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Опубликовать"), KeyboardButton(text="❌ Отменить")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
PRICE_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Не указывать")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


MENU_TEXTS = {
    "🚚 Найти груз",
    "📦 Разместить заявку",
    "🚛 Свободные автомобили",
    "👤 Мой профиль",
}


@dp.message(F.text.in_(MENU_TEXTS))
async def interrupt_form_with_menu(message: Message, state: FSMContext) -> None:
    # A menu tap must never be consumed as an answer to the active form field.
    if await state.get_state():
        await state.clear()
        await message.answer("Текущий черновик заявки отменён. Открываю выбранный раздел.", reply_markup=MAIN_MENU)
    if message.text == "🚚 Найти груз":
        await find_loads(message)
    elif message.text == "📦 Разместить заявку":
        await begin_placement(message, state)
    elif message.text == "🚛 Свободные автомобили":
        await find_vehicles(message)
    elif message.text == "👤 Мой профиль":
        await show_profile(message)


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=message.from_user.id, telegram_username=message.from_user.username)
            session.add(user)
            await session.commit()
        registered = bool(user.full_name)
    if not registered:
        await message.answer("Добро пожаловать в CargoLink!\n\nДля регистрации напишите имя и фамилию.")
        return
    await message.answer("С возвращением в CargoLink. Выберите раздел:", reply_markup=MAIN_MENU)


@dp.message(Command("cancel"))
@dp.message(F.text == "❌ Отменить")
async def cancel_form(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Создание заявки отменено.", reply_markup=MAIN_MENU)


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
    await message.answer("Номер сохранён в профиле и не публикуется в заявках.", reply_markup=MAIN_MENU)


@dp.message(F.text == "📦 Разместить заявку")
async def begin_placement(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
    if not user or not user.full_name:
        await message.answer("Сначала завершите регистрацию командой /start.")
        return
    await state.clear()
    await state.set_state(PlacementForm.origin)
    await message.answer("📍 Укажите город и адрес загрузки:", reply_markup=ReplyKeyboardRemove())


@dp.message(PlacementForm.origin)
async def placement_origin(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 3:
        await message.answer("Укажите город и адрес загрузки подробнее.")
        return
    await state.update_data(origin=value[:300])
    await state.set_state(PlacementForm.destination)
    await message.answer("📍 Укажите город и адрес выгрузки:")


@dp.message(PlacementForm.destination)
async def placement_destination(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 3:
        await message.answer("Укажите город и адрес выгрузки подробнее.")
        return
    await state.update_data(destination=value[:300])
    await state.set_state(PlacementForm.cargo)
    await message.answer("📦 Что перевозим? Укажите наименование груза и особенности (если есть):")


@dp.message(PlacementForm.cargo)
async def placement_cargo(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("Укажите наименование груза.")
        return
    await state.update_data(cargo=value[:300])
    await state.set_state(PlacementForm.weight)
    await message.answer("⚖️ Укажите массу груза в тоннах. Например: 20")


@dp.message(PlacementForm.weight)
async def placement_weight(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        weight = float(raw)
        if not 0 < weight <= 100000:
            raise ValueError
    except ValueError:
        await message.answer("Введите массу числом в тоннах, например 20 или 1.5.")
        return
    await state.update_data(weight_tons=weight)
    await state.set_state(PlacementForm.vehicle)
    await message.answer("🚛 Какой транспорт требуется? Например: тент 20 т, цистерна, рефрижератор, самосвал.")


@dp.message(PlacementForm.vehicle)
async def placement_vehicle(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("Укажите тип необходимого транспорта.")
        return
    await state.update_data(vehicle_type=value[:200])
    await state.set_state(PlacementForm.pickup_date)
    await message.answer("📅 Укажите дату и желаемое время загрузки. Например: 05.11.2026, утро.")


@dp.message(PlacementForm.pickup_date)
async def placement_date(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 3:
        await message.answer("Укажите дату и время загрузки.")
        return
    await state.update_data(pickup_date=value[:100])
    await state.set_state(PlacementForm.price)
    await message.answer("💰 Укажите бюджет/ставку в рублях или нажмите «Не указывать».", reply_markup=PRICE_MENU)


@dp.message(PlacementForm.price)
async def placement_price(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Укажите сумму или нажмите «Не указывать».")
        return
    await state.update_data(price_rub=None if value.lower() == "не указывать" else value[:100])
    data = await state.get_data()
    summary = (
        "Проверьте заявку перед публикацией:\n\n"
        f"Загрузка: {data['origin']}\n"
        f"Выгрузка: {data['destination']}\n"
        f"Груз: {data['cargo']}\n"
        f"Масса: {data['weight_tons']} т\n"
        f"Транспорт: {data['vehicle_type']}\n"
        f"Дата: {data['pickup_date']}\n"
        f"Ставка: {data['price_rub'] or 'не указана'}\n\n"
        "Нажмите «Опубликовать», чтобы сохранить заявку."
    )
    await state.set_state(PlacementForm.confirm)
    await message.answer(summary, reply_markup=CONFIRM_MENU)


@dp.message(PlacementForm.confirm, F.text == "✅ Опубликовать")
async def publish_placement(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            await state.clear()
            await message.answer("Пользователь не найден. Отправьте /start.", reply_markup=MAIN_MENU)
            return
        request = CargoRequest(
            customer_id=user.id,
            origin=data["origin"],
            destination=data["destination"],
            cargo=data["cargo"],
            weight_tons=data["weight_tons"],
            vehicle_type=data["vehicle_type"],
            pickup_date=data["pickup_date"],
            price_rub=data["price_rub"],
            status="open",
        )
        session.add(request)
        await session.commit()
        request_id = request.id
    await state.clear()
    await message.answer(
        f"✅ Заявка №{request_id} сохранена в CargoLink.\n"
        "На следующем этапе подключим публикацию для перевозчиков и отклики.",
        reply_markup=MAIN_MENU,
    )


@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message) -> None:
    if not message.from_user:
        return
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
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


@dp.message(F.text == "🚚 Найти груз")
async def find_loads(message: Message) -> None:
    await message.answer("Поиск и фильтры грузов подключим следующим этапом.", reply_markup=MAIN_MENU)


@dp.message(F.text == "🚛 Свободные автомобили")
async def find_vehicles(message: Message) -> None:
    await message.answer("Каталог свободных автомобилей подключим следующим этапом.", reply_markup=MAIN_MENU)


@dp.message(F.text)
async def text_router(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    incoming = message.text.strip()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            await message.answer("Для начала регистрации отправьте /start.")
            return
        if not user.full_name and len(incoming) >= 3 and not incoming.startswith("/"):
            user.full_name = incoming[:200]
            user.telegram_username = message.from_user.username
            await session.commit()
            await message.answer("Спасибо! Теперь отправьте свой номер кнопкой ниже.", reply_markup=CONTACT_MENU)
            return
    await message.answer("Выберите действие с помощью кнопок меню.", reply_markup=MAIN_MENU)


async def main() -> None:
    token = settings.bot_token.strip()
    if not token or token == "PASTE_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError("Не задан BOT_TOKEN. Добавьте токен в переменные окружения или файл .env.")
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = Bot(token=token)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
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
