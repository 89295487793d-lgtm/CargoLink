import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from sqlalchemy import select, text

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import CargoChat, CargoChatMessage, CargoRequest, CargoStatusEvent, CarrierOffer, User

settings = get_settings()
dp = Dispatcher()
logger = logging.getLogger("cargolink.bot")


class ChatForm(StatesGroup):
    active = State()


class OfferForm(StatesGroup):
    price = State()
    vat = State()
    vehicle = State()
    completion_date = State()
    comment = State()
    confirm = State()


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
        [KeyboardButton(text="📨 Мои предложения"), KeyboardButton(text="📋 Мои заявки")],
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
    "📨 Мои предложения",
    "📋 Мои заявки",
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
    elif message.text == "📨 Мои предложения":
        await show_my_offers(message)
    elif message.text == "📋 Мои заявки":
        await show_my_requests(message)


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
    async with SessionLocal() as session:
        result = await session.execute(
            select(CargoRequest)
            .where(CargoRequest.status == "open")
            .order_by(CargoRequest.created_at.desc())
            .limit(10)
        )
        requests = result.scalars().all()
    if not requests:
        await message.answer("Пока открытых заявок нет.", reply_markup=MAIN_MENU)
        return
    await message.answer("🚚 Открытые заявки CargoLink:", reply_markup=MAIN_MENU)
    for item in requests:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Подробнее и предложить ставку", callback_data=f"cargo:view:{item.id}")
        ]])
        await message.answer(
            f"Заявка №{item.id}\n"
            f"Маршрут: {item.origin} → {item.destination}\n"
            f"Груз: {item.cargo}\n"
            f"Масса: {item.weight_tons:g} т\n"
            f"Транспорт: {item.vehicle_type}\n"
            f"Дата загрузки: {item.pickup_date}\n"
            f"Бюджет заказчика: {item.price_rub or 'не указан'}",
            reply_markup=keyboard,
        )



@dp.callback_query(F.data.startswith("cargo:view:"))
async def cargo_view(callback: CallbackQuery) -> None:
    request_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        result = await session.execute(select(CargoRequest).where(CargoRequest.id == request_id))
        item = result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        viewer = user_result.scalar_one_or_none()
    if item is None or item.status != "open":
        await callback.answer("Заявка уже недоступна.", show_alert=True)
        return
    if viewer and viewer.id == item.customer_id:
        await callback.answer("Это ваша заявка.", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Предложить ставку", callback_data=f"offer:start:{item.id}")
    ]])
    await callback.message.answer(
        f"📄 Заявка №{item.id}\n\nМаршрут: {item.origin} → {item.destination}\n"
        f"Груз: {item.cargo}\nМасса: {item.weight_tons:g} т\n"
        f"Требуемый транспорт: {item.vehicle_type}\nЗагрузка: {item.pickup_date}\n"
        f"Бюджет: {item.price_rub or 'не указан'}",
        reply_markup=keyboard,
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("offer:start:"))
async def offer_start(callback: CallbackQuery, state: FSMContext) -> None:
    request_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        result = await session.execute(select(CargoRequest).where(CargoRequest.id == request_id))
        item = result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        carrier = user_result.scalar_one_or_none()
    if item is None or item.status != "open":
        await callback.answer("Заявка уже закрыта.", show_alert=True)
        return
    if carrier is None or not carrier.full_name:
        await callback.answer("Сначала зарегистрируйтесь через /start.", show_alert=True)
        return
    if carrier.id == item.customer_id:
        await callback.answer("Нельзя предложить ставку на собственную заявку.", show_alert=True)
        return
    await state.clear()
    await state.update_data(offer_request_id=request_id)
    await state.set_state(OfferForm.price)
    await callback.message.answer(f"💰 Ваша ставка по заявке №{request_id}, ₽. Введите сумму:")
    await callback.answer()


@dp.message(OfferForm.price)
async def offer_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(" ", "").replace(",", ".")
    try:
        value = float(raw)
        if not 0 < value <= 1_000_000_000:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительную сумму в рублях, например 85000.")
        return
    await state.update_data(offer_price=value)
    await state.set_state(OfferForm.vat)
    vat_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="С НДС"), KeyboardButton(text="Без НДС")]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer("Укажите налоговый режим ставки:", reply_markup=vat_menu)


@dp.message(OfferForm.vat)
async def offer_vat(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if value not in {"С НДС", "Без НДС"}:
        await message.answer("Выберите «С НДС» или «Без НДС».")
        return
    await state.update_data(offer_vat=value)
    await state.set_state(OfferForm.vehicle)
    await message.answer("🚛 Укажите транспорт, которым выполните перевозку:", reply_markup=ReplyKeyboardRemove())


@dp.message(OfferForm.vehicle)
async def offer_vehicle(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 2:
        await message.answer("Укажите тип транспорта подробнее.")
        return
    await state.update_data(offer_vehicle=value[:200])
    await state.set_state(OfferForm.completion_date)
    await message.answer("📅 Укажите дату или срок выполнения перевозки:")


@dp.message(OfferForm.completion_date)
async def offer_date(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 3:
        await message.answer("Укажите дату или срок выполнения.")
        return
    await state.update_data(offer_date=value[:100])
    await state.set_state(OfferForm.comment)
    comment_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Без комментария")]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer("💬 Добавьте комментарий заказчику или нажмите «Без комментария»:", reply_markup=comment_menu)


@dp.message(OfferForm.comment)
async def offer_comment(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Напишите комментарий или нажмите «Без комментария».")
        return
    comment = None if value == "Без комментария" else value[:500]
    await state.update_data(offer_comment=comment)
    data = await state.get_data()
    summary = (
        "Проверьте предложение перед отправкой:\n\n"
        f"Заявка №{data['offer_request_id']}\n"
        f"Ставка: {data['offer_price']:,.2f} ₽\n"
        f"НДС: {data['offer_vat']}\n"
        f"Транспорт: {data['offer_vehicle']}\n"
        f"Срок: {data['offer_date']}\n"
        f"Комментарий: {comment or 'нет'}\n\nОтправить предложение заказчику?"
    )
    confirm = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📨 Отправить предложение"), KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await state.set_state(OfferForm.confirm)
    await message.answer(summary, reply_markup=confirm)


@dp.message(OfferForm.confirm, F.text == "📨 Отправить предложение")
async def offer_submit(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    async with SessionLocal() as session:
        carrier_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        carrier = carrier_result.scalar_one_or_none()
        request_result = await session.execute(select(CargoRequest).where(CargoRequest.id == data["offer_request_id"]))
        cargo = request_result.scalar_one_or_none()
        if not carrier or not cargo or cargo.status != "open" or cargo.customer_id == carrier.id:
            await state.clear()
            await message.answer("Заявка больше недоступна. Предложение не отправлено.", reply_markup=MAIN_MENU)
            return
        offer = CarrierOffer(
            request_id=cargo.id, carrier_id=carrier.id, price_rub=data["offer_price"],
            vat_mode=data["offer_vat"], vehicle_type=data["offer_vehicle"],
            completion_date=data["offer_date"], comment=data.get("offer_comment"), status="pending",
        )
        session.add(offer)
        await session.commit()
        offer_id = offer.id
        customer_result = await session.execute(select(User).where(User.id == cargo.customer_id))
        customer = customer_result.scalar_one_or_none()
        customer_chat = customer.telegram_id if customer else None
        route = f"{cargo.origin} → {cargo.destination}"
        carrier_name = carrier.full_name or "Перевозчик"
    await state.clear()
    await message.answer(
        f"✅ Предложение №{offer_id} отправлено по заявке №{data['offer_request_id']}.\nСтатус: ожидает решения заказчика.",
        reply_markup=MAIN_MENU,
    )
    if customer_chat:
        decision = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"offer:accept:{offer_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"offer:reject:{offer_id}"),
        ]])
        try:
            await message.bot.send_message(
                customer_chat,
                f"📨 Новое предложение по заявке №{data['offer_request_id']}!\n\n"
                f"Перевозчик: {carrier_name}\nМаршрут: {route}\n"
                f"Ставка: {data['offer_price']:,.2f} ₽ ({data['offer_vat']})\n"
                f"Транспорт: {data['offer_vehicle']}\nСрок: {data['offer_date']}\n"
                f"Комментарий: {data.get('offer_comment') or 'нет'}",
                reply_markup=decision,
            )
        except Exception:
            logger.exception("Could not notify customer about offer %s", offer_id)
            await message.answer("Предложение сохранено, но уведомление не доставлено. Заказчик увидит его в разделе «Мои заявки».")


@dp.message(OfferForm.confirm, F.text == "❌ Отменить")
async def offer_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отправка предложения отменена.", reply_markup=MAIN_MENU)


@dp.callback_query(F.data.startswith("offer:accept:"))
async def offer_accept(callback: CallbackQuery) -> None:
    offer_id = int(callback.data.rsplit(":", 1)[1])
    other_carriers = []
    async with SessionLocal() as session:
        result = await session.execute(select(CarrierOffer).where(CarrierOffer.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            await callback.answer("Предложение не найдено.", show_alert=True)
            return
        request_result = await session.execute(select(CargoRequest).where(CargoRequest.id == offer.request_id))
        cargo = request_result.scalar_one_or_none()
        customer_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        customer = customer_result.scalar_one_or_none()
        if not customer or not cargo or cargo.customer_id != customer.id:
            await callback.answer("Только заказчик может принять это предложение.", show_alert=True)
            return
        if offer.status != "pending" or cargo.status != "open":
            await callback.answer("Это предложение уже обработано.", show_alert=True)
            return
        offer.status = "accepted"
        cargo.status = "closed"
        cargo.delivery_status = "accepted"
        cargo.delivery_updated_at = datetime.now(timezone.utc)
        cargo.delivery_updated_by = customer.id
        session.add(CargoStatusEvent(request_id=cargo.id, actor_id=customer.id, status="accepted"))
        other_result = await session.execute(
            select(CarrierOffer).where(CarrierOffer.request_id == cargo.id, CarrierOffer.id != offer.id, CarrierOffer.status == "pending")
        )
        others = other_result.scalars().all()
        for other in others:
            other.status = "rejected"
            other_carriers.append((other.id, other.carrier_id))
        carrier_result = await session.execute(select(User).where(User.id == offer.carrier_id))
        carrier = carrier_result.scalar_one_or_none()
        carrier_chat = carrier.telegram_id if carrier else None
        chat_result = await session.execute(select(CargoChat).where(CargoChat.offer_id == offer.id))
        chat = chat_result.scalar_one_or_none()
        if chat is None:
            chat = CargoChat(request_id=cargo.id, offer_id=offer.id, customer_id=customer.id, carrier_id=offer.carrier_id, status="active")
            session.add(chat)
            await session.flush()
        chat_id = chat.id
        await session.commit()
        route = f"{cargo.origin} → {cargo.destination}"
        cargo_id = cargo.id
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Вы приняли предложение №{offer_id}. Заявка №{cargo_id} закрыта для новых ставок.")
    chat_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Открыть переписку", callback_data=f"chat:open:{chat_id}")
    ]])
    await callback.bot.send_message(
        callback.from_user.id,
        f"💬 По заявке №{cargo_id} создана переписка с перевозчиком. Маршрут: {route}.",
        reply_markup=chat_keyboard,
    )
    if carrier_chat:
        await callback.bot.send_message(
            carrier_chat,
            f"🎉 Заказчик принял ваше предложение №{offer_id} по заявке №{cargo_id} ({route}).\n"
            "Теперь можно обсудить детали перевозки в CargoLink.",
            reply_markup=chat_keyboard,
        )
    for other_id, carrier_id in other_carriers:
        async with SessionLocal() as session:
            user_result = await session.execute(select(User).where(User.id == carrier_id))
            user = user_result.scalar_one_or_none()
            chat_id = user.telegram_id if user else None
        if chat_id:
            try:
                await callback.bot.send_message(chat_id, f"Предложение №{other_id} по заявке №{cargo_id} закрыто: заказчик выбрал другого перевозчика.")
            except Exception:
                logger.exception("Could not notify carrier about offer %s", other_id)
    await callback.answer("Предложение принято.")



@dp.callback_query(F.data.startswith("chat:open:"))
async def open_cargo_chat(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        result = await session.execute(select(CargoChat).where(CargoChat.id == chat_id, CargoChat.status == "active"))
        chat = result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        if not chat or not user or user.id not in {chat.customer_id, chat.carrier_id}:
            await callback.answer("Переписка недоступна.", show_alert=True)
            return
        other_id = chat.carrier_id if user.id == chat.customer_id else chat.customer_id
        other_result = await session.execute(select(User).where(User.id == other_id))
        other = other_result.scalar_one_or_none()
        history_result = await session.execute(
            select(CargoChatMessage).where(CargoChatMessage.chat_id == chat.id)
            .order_by(CargoChatMessage.created_at.asc()).limit(30)
        )
        history = history_result.scalars().all()
        request_result = await session.execute(select(CargoRequest).where(CargoRequest.id == chat.request_id))
        cargo = request_result.scalar_one_or_none()
    await state.clear()
    await state.set_state(ChatForm.active)
    await state.update_data(chat_id=chat_id)
    chat_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="↩️ Выйти из чата")]],
        resize_keyboard=True,
    )
    finish_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔒 Завершить переписку", callback_data=f"chat:finish:ask:{chat_id}")
    ]])
    await callback.message.answer(
        f"💬 Переписка по заявке №{chat.request_id}\n"
        f"Маршрут: {cargo.origin if cargo else ''} → {cargo.destination if cargo else ''}\n"
        f"Собеседник: {other.full_name if other else 'участник CargoLink'}\n\n"
        "Можно отправлять текст, фотографии, PDF и другие документы. "
        "Вложения будут доставлены второму участнику.",
        reply_markup=chat_menu,
    )
    await callback.message.answer("Управление перепиской:", reply_markup=finish_keyboard)
    if history:
        lines = ["Последние сообщения:"]
        for item in history:
            sender = "Вы" if item.sender_id == user.id else (other.full_name if other else "Собеседник")
            stamp = item.created_at.strftime("%d.%m %H:%M") if item.created_at else ""
            lines.append(f"[{stamp}] {sender}: {item.body}")
        await callback.message.answer("\n".join(lines))
    else:
        await callback.message.answer("Переписка пока пустая. Напишите первое сообщение или отправьте файл.")
    await callback.answer()


@dp.message(ChatForm.active, F.text == "↩️ Выйти из чата")
async def close_chat_view(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Вы вышли из режима переписки. История сохранена.", reply_markup=MAIN_MENU)


@dp.callback_query(F.data.startswith("chat:finish:ask:"))
async def ask_finish_cargo_chat(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да, завершить", callback_data=f"chat:finish:confirm:{chat_id}"),
        InlineKeyboardButton(text="Отмена", callback_data=f"chat:finish:cancel:{chat_id}"),
    ]])
    await callback.message.answer(
        "Завершить переписку по этой заявке? После подтверждения отправка новых сообщений будет отключена для обоих участников.",
        reply_markup=keyboard,
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("chat:finish:cancel:"))
async def cancel_finish_cargo_chat(callback: CallbackQuery) -> None:
    await callback.answer("Переписка остаётся активной.")


@dp.callback_query(F.data.startswith("chat:finish:confirm:"))
async def finish_cargo_chat(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    participant_ids = []
    request_id = None
    async with SessionLocal() as session:
        result = await session.execute(select(CargoChat).where(CargoChat.id == chat_id))
        chat = result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        if not chat or not user or user.id not in {chat.customer_id, chat.carrier_id}:
            await callback.answer("Нет доступа к этой переписке.", show_alert=True)
            return
        if chat.status != "active":
            await callback.answer("Переписка уже завершена.", show_alert=True)
            return
        chat.status = "closed"
        participant_ids = [chat.customer_id, chat.carrier_id]
        request_id = chat.request_id
        await session.commit()
        users_result = await session.execute(select(User).where(User.id.in_(participant_ids)))
        recipients = users_result.scalars().all()
        telegram_ids = [item.telegram_id for item in recipients]
    await state.clear()
    await callback.message.answer(f"🔒 Переписка по заявке №{request_id} завершена.", reply_markup=MAIN_MENU)
    for telegram_id in telegram_ids:
        if telegram_id != callback.from_user.id:
            try:
                await callback.bot.send_message(telegram_id, f"🔒 Переписка по заявке №{request_id} завершена вторым участником.")
            except Exception:
                logger.exception("Could not notify participant that chat %s was closed", chat_id)
    await callback.answer("Переписка завершена.")


@dp.message(ChatForm.active, F.text)
async def relay_chat_message(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    data = await state.get_data()
    chat_id = data.get("chat_id")
    async with SessionLocal() as session:
        chat_result = await session.execute(select(CargoChat).where(CargoChat.id == chat_id, CargoChat.status == "active"))
        chat = chat_result.scalar_one_or_none()
        sender_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        sender = sender_result.scalar_one_or_none()
        if not chat or not sender or sender.id not in {chat.customer_id, chat.carrier_id}:
            await state.clear()
            await message.answer("Переписка недоступна. Откройте её заново из уведомления.", reply_markup=MAIN_MENU)
            return
        recipient_id = chat.carrier_id if sender.id == chat.customer_id else chat.customer_id
        recipient_result = await session.execute(select(User).where(User.id == recipient_id))
        recipient = recipient_result.scalar_one_or_none()
        if not recipient:
            await message.answer("Не удалось найти второго участника переписки.")
            return
        body = message.text.strip()
        if not body or len(body) > 4000:
            await message.answer("Сообщение должно содержать от 1 до 4000 символов.")
            return
        record = CargoChatMessage(chat_id=chat.id, sender_id=sender.id, body=body, content_type="text")
        session.add(record)
        await session.commit()
        recipient_chat_id = recipient.telegram_id
        sender_name = sender.full_name or "Участник CargoLink"
        request_id = chat.request_id
    try:
        await message.bot.send_message(
            recipient_chat_id,
            f"💬 Заявка №{request_id} · {sender_name}:\n{body}",
        )
        await message.answer("✓ Доставлено.")
    except Exception:
        logger.exception("Could not relay chat message for chat %s", chat_id)
        await message.answer("Сообщение сохранено, но Telegram не подтвердил доставку. Попробуйте позже.")


@dp.message(
    ChatForm.active,
    F.photo | F.document | F.video | F.audio | F.voice | F.video_note | F.animation | F.sticker,
)
async def relay_chat_attachment(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    chat_id = data.get("chat_id")
    content_type = message.content_type.value if hasattr(message.content_type, "value") else str(message.content_type)
    media = None
    if message.photo:
        media = message.photo[-1]
    else:
        for field in ("document", "video", "audio", "voice", "video_note", "animation", "sticker"):
            candidate = getattr(message, field, None)
            if candidate:
                media = candidate
                break
    file_id = media.file_id if media else None
    caption = (message.caption or "").strip()[:1000]
    labels = {
        "photo": "Фотография", "document": "Документ", "video": "Видео",
        "audio": "Аудио", "voice": "Голосовое сообщение", "video_note": "Видеосообщение",
        "animation": "Анимация", "sticker": "Стикер",
    }
    body = caption or f"[{labels.get(content_type, 'Вложение')}]"
    async with SessionLocal() as session:
        chat_result = await session.execute(select(CargoChat).where(CargoChat.id == chat_id, CargoChat.status == "active"))
        chat = chat_result.scalar_one_or_none()
        sender_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        sender = sender_result.scalar_one_or_none()
        if not chat or not sender or sender.id not in {chat.customer_id, chat.carrier_id}:
            await state.clear()
            await message.answer("Переписка недоступна. Откройте её заново из раздела сделок.", reply_markup=MAIN_MENU)
            return
        recipient_id = chat.carrier_id if sender.id == chat.customer_id else chat.customer_id
        recipient_result = await session.execute(select(User).where(User.id == recipient_id))
        recipient = recipient_result.scalar_one_or_none()
        if not recipient:
            await message.answer("Не удалось найти второго участника переписки.")
            return
        record = CargoChatMessage(
            chat_id=chat.id, sender_id=sender.id, body=body,
            content_type=content_type, file_id=file_id,
        )
        session.add(record)
        await session.commit()
        recipient_telegram_id = recipient.telegram_id
        sender_name = sender.full_name or "Участник CargoLink"
        request_id = chat.request_id
    try:
        await message.bot.send_message(
            recipient_telegram_id,
            f"📎 Вложение по заявке №{request_id} от {sender_name}: {labels.get(content_type, 'Файл')}",
        )
        await message.bot.copy_message(
            chat_id=recipient_telegram_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        await message.answer("✓ Вложение доставлено.")
    except Exception:
        logger.exception("Could not relay attachment for chat %s", chat_id)
        await message.answer("Вложение сохранено в истории, но Telegram не подтвердил доставку.")





@dp.callback_query(F.data.startswith("offer:reject:"))
async def offer_reject(callback: CallbackQuery) -> None:
    offer_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        result = await session.execute(select(CarrierOffer).where(CarrierOffer.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            await callback.answer("Предложение не найдено.", show_alert=True)
            return
        request_result = await session.execute(select(CargoRequest).where(CargoRequest.id == offer.request_id))
        cargo = request_result.scalar_one_or_none()
        customer_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        customer = customer_result.scalar_one_or_none()
        if not customer or not cargo or cargo.customer_id != customer.id:
            await callback.answer("Только заказчик может отклонить это предложение.", show_alert=True)
            return
        if offer.status != "pending":
            await callback.answer("Предложение уже обработано.", show_alert=True)
            return
        offer.status = "rejected"
        carrier_result = await session.execute(select(User).where(User.id == offer.carrier_id))
        carrier = carrier_result.scalar_one_or_none()
        carrier_chat = carrier.telegram_id if carrier else None
        request_id = cargo.id
        await session.commit()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"Предложение №{offer_id} отклонено.")
    if carrier_chat:
        await callback.bot.send_message(carrier_chat, f"Заказчик отклонил предложение №{offer_id} по заявке №{request_id}.")
    await callback.answer("Предложение отклонено.")


@dp.callback_query(F.data.startswith("delivery:loading:"))
async def delivery_loading(callback: CallbackQuery) -> None:
    request_id = int(callback.data.rsplit(":", 1)[1])
    recipients = []
    actor_name = ""
    async with SessionLocal() as session:
        cargo_result = await session.execute(select(CargoRequest).where(CargoRequest.id == request_id))
        cargo = cargo_result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        actor = user_result.scalar_one_or_none()
        offer_result = await session.execute(select(CarrierOffer).where(CarrierOffer.request_id == request_id, CarrierOffer.status == "accepted"))
        offer = offer_result.scalar_one_or_none()
        if not cargo or not actor or not offer or offer.carrier_id != actor.id:
            await callback.answer("Только выбранный перевозчик может начать загрузку.", show_alert=True)
            return
        if cargo.delivery_status != "accepted":
            await callback.answer("Статус уже изменён. Обновите список заявок.", show_alert=True)
            return
        cargo.delivery_status = "in_transit"
        cargo.delivery_updated_at = datetime.now(timezone.utc)
        cargo.delivery_updated_by = actor.id
        session.add(CargoStatusEvent(request_id=request_id, actor_id=actor.id, status="in_transit"))
        parties = await session.execute(select(User).where(User.id.in_([cargo.customer_id, offer.carrier_id])))
        recipients = [u.telegram_id for u in parties.scalars().all()]
        actor_name = actor.full_name or "Участник CargoLink"
        await session.commit()
    stamp = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    for telegram_id in recipients:
        await callback.bot.send_message(telegram_id, f"🚚 По заявке №{request_id} статус изменён на «Груз в пути». Изменил: {actor_name}. Время: {stamp}.")
    await callback.answer("Статус: Груз в пути.")
    await callback.message.edit_reply_markup(reply_markup=None)

@dp.callback_query(F.data.startswith("delivery:delivered:"))
async def delivery_delivered(callback: CallbackQuery) -> None:
    request_id = int(callback.data.rsplit(":", 1)[1])
    recipients = []
    actor_name = ""
    async with SessionLocal() as session:
        cargo_result = await session.execute(select(CargoRequest).where(CargoRequest.id == request_id))
        cargo = cargo_result.scalar_one_or_none()
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        actor = user_result.scalar_one_or_none()
        offer_result = await session.execute(select(CarrierOffer).where(CarrierOffer.request_id == request_id, CarrierOffer.status == "accepted"))
        offer = offer_result.scalar_one_or_none()
        allowed = {cargo.customer_id, offer.carrier_id if offer else None} if cargo else set()
        if not cargo or not actor or actor.id not in allowed:
            await callback.answer("Нет доступа к изменению статуса этой перевозки.", show_alert=True)
            return
        if cargo.delivery_status != "in_transit":
            await callback.answer("Перевозка уже завершена или статус изменён.", show_alert=True)
            return
        cargo.delivery_status = "delivered"
        cargo.delivery_updated_at = datetime.now(timezone.utc)
        cargo.delivery_updated_by = actor.id
        session.add(CargoStatusEvent(request_id=request_id, actor_id=actor.id, status="delivered"))
        parties = await session.execute(select(User).where(User.id.in_([cargo.customer_id, offer.carrier_id])))
        recipients = [u.telegram_id for u in parties.scalars().all()]
        actor_name = actor.full_name or "Участник CargoLink"
        await session.commit()
    stamp = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    for telegram_id in recipients:
        await callback.bot.send_message(telegram_id, f"✅ По заявке №{request_id} статус изменён на «Доставлено». Подтвердил: {actor_name}. Время: {stamp}.")
    await callback.answer("Перевозка отмечена как доставленная.")
    await callback.message.edit_reply_markup(reply_markup=None)

@dp.message(F.text == "📨 Мои предложения")
async def show_my_offers(message: Message) -> None:
    if not message.from_user:
        return
    async with SessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала отправьте /start.")
            return
        result = await session.execute(
            select(CarrierOffer, CargoRequest).join(CargoRequest, CarrierOffer.request_id == CargoRequest.id)
            .where(CarrierOffer.carrier_id == user.id).order_by(CarrierOffer.created_at.desc()).limit(20)
        )
        rows = result.all()
    if not rows:
        await message.answer("Вы пока не отправляли предложения.", reply_markup=MAIN_MENU)
        return
    names = {"pending": "Ожидает решения", "accepted": "Принято", "rejected": "Отклонено"}
    await message.answer("📨 Ваши предложения:", reply_markup=MAIN_MENU)
    for offer, cargo in rows:
        text_value = (
            f"Предложение №{offer.id} · заявка №{cargo.id}\n"
            f"{cargo.origin} → {cargo.destination}\n"
            f"{offer.price_rub:,.2f} ₽ · {offer.vat_mode}\n"
            f"Статус: {names.get(offer.status, offer.status)}"
        )
        keyboard = None
        if offer.status == "accepted":
            async with SessionLocal() as session:
                chat_result = await session.execute(select(CargoChat).where(CargoChat.offer_id == offer.id))
                chat = chat_result.scalar_one_or_none()
            if chat:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="💬 Открыть чат по заявке", callback_data=f"chat:open:{chat.id}")
                ]])
        await message.answer(text_value, reply_markup=keyboard)


@dp.message(F.text == "📋 Мои заявки")
async def show_my_requests(message: Message) -> None:
    if not message.from_user:
        return
    async with SessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала отправьте /start.")
            return
        result = await session.execute(
            select(CargoRequest).where(CargoRequest.customer_id == user.id).order_by(CargoRequest.created_at.desc()).limit(20)
        )
        requests = result.scalars().all()
    if not requests:
        await message.answer("У вас пока нет заявок.", reply_markup=MAIN_MENU)
        return
    names = {"open": "Открыта", "closed": "Закрыта"}
    for cargo in requests:
        async with SessionLocal() as session:
            offer_result = await session.execute(select(CarrierOffer).where(CarrierOffer.request_id == cargo.id).order_by(CarrierOffer.created_at.desc()))
            offers = offer_result.scalars().all()
        lines = [f"📋 Заявка №{cargo.id}: {cargo.origin} → {cargo.destination}", f"Статус: {names.get(cargo.status, cargo.status)}"]
        if not offers:
            lines.append("Предложений пока нет.")
        for offer in offers:
            lines.append(f"Предложение №{offer.id}: {offer.price_rub:,.2f} ₽ ({offer.vat_mode}) — {offer.status}")
        async with SessionLocal() as session:
            chat_result = await session.execute(
                select(CargoChat).where(CargoChat.request_id == cargo.id, CargoChat.status == "active")
            )
            chat = chat_result.scalar_one_or_none()
        keyboard = None
        if chat:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💬 Открыть чат по заявке", callback_data=f"chat:open:{chat.id}")
            ]])
        await message.answer("\n".join(lines), reply_markup=keyboard or MAIN_MENU)


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
