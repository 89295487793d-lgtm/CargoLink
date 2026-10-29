import hashlib, hmac, json, os, time
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException
from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import User

cfg = settings()

def validate_init_data(init_data: str, token: str) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    supplied_hash = pairs.pop("hash", None)
    if not supplied_hash:
        raise ValueError("Missing Telegram init data hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied_hash):
        raise ValueError("Invalid Telegram init data signature")
    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > 86400:
        raise ValueError("Telegram init data expired")
    user = json.loads(pairs.get("user", "{}"))
    if not user.get("id"):
        raise ValueError("Telegram user missing")
    return user

async def current_user(x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data")) -> User:
    if cfg.dev_auth and not x_telegram_init_data:
        # Development-only identity for local browser testing.
        tg_id, username, first_name = 999000001, "dev_user", "CargoLink Demo"
    else:
        if not cfg.bot_token or not x_telegram_init_data:
            raise HTTPException(status_code=401, detail="Open CargoLink inside Telegram.")
        try:
            data = validate_init_data(x_telegram_init_data, cfg.bot_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired Telegram session.")
        tg_id = int(data["id"])
        username = data.get("username")
        first_name = " ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or "Пользователь"
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar_one_or_none()
        if user is None:
            user = User(telegram_id=tg_id, username=username, fio=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user
