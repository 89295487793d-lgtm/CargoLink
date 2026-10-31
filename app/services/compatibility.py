from datetime import datetime, timezone

def check_liquid_dangerous_goods(*, cargo: dict, vehicle: dict, tank: dict, documents: list[dict] | None = None) -> dict:
    """Preliminary rule engine only; it does not certify legal compliance."""
    reasons = []
    un_number = str(cargo.get("un_number", "")).replace("UN", "").strip().upper()
    allowed = {str(value).replace("UN", "").strip().upper() for value in (tank.get("allowed_un_numbers") or [])}
    if not un_number:
        reasons.append({"code":"UN_NUMBER_MISSING","severity":"manual","message":"Не указан номер ООН"})
    if un_number and allowed and un_number not in allowed:
        reasons.append({"code":"PRODUCT_NOT_ALLOWED","severity":"block","message":"Продукт не указан среди разрешённых для цистерны"})
    if not allowed:
        reasons.append({"code":"COMPATIBILITY_DATA_MISSING","severity":"manual","message":"Нет подтверждённых данных о совместимости"})
    volume = cargo.get("volume_m3")
    capacity = tank.get("total_volume_m3")
    if volume is not None and capacity is not None and volume > capacity:
        reasons.append({"code":"TANK_CAPACITY_EXCEEDED","severity":"block","message":"Объём груза превышает объём цистерны"})
    if cargo.get("pump_required") and not tank.get("pump"):
        reasons.append({"code":"PUMP_REQUIRED","severity":"block","message":"Требуется насосное оборудование"})
    now = datetime.now(timezone.utc)
    for doc in documents or []:
        expiry = doc.get("expires_at")
        if expiry and expiry <= now:
            reasons.append({"code":"DOCUMENT_EXPIRED","severity":"block","message":f"Истёк документ: {doc.get('document_type','неизвестно')}"})
        if doc.get("verification_status") != "verified":
            reasons.append({"code":"DOCUMENT_NOT_VERIFIED","severity":"manual","message":f"Не проверен документ: {doc.get('document_type','неизвестно')}"})
    result = "blocked" if any(x["severity"] == "block" for x in reasons) else "manual_review" if reasons else "eligible"
    return {"result":result,"reasons":reasons,"is_legal_certification":False}
