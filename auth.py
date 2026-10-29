from fastapi import Header, HTTPException
from typing import Optional

# DEVELOPMENT ONLY. Replace with Telegram WebApp initData signature validation before public launch.
def get_telegram_user(x_telegram_id: Optional[str] = Header(default=None)) -> int:
    if not x_telegram_id or not x_telegram_id.isdigit():
        raise HTTPException(status_code=401, detail="Откройте CargoLink из Telegram")
    return int(x_telegram_id)
