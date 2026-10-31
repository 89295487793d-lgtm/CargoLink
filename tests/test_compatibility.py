from app.services.compatibility import check_liquid_dangerous_goods

def test_missing_product_compatibility_requires_manual_review():
    result = check_liquid_dangerous_goods(cargo={"un_number":"1202","volume_m3":10}, vehicle={},
        tank={"total_volume_m3":30,"allowed_un_numbers":[],"pump":False})
    assert result["result"] == "manual_review"
    assert result["is_legal_certification"] is False

def test_incompatible_product_is_blocked():
    result = check_liquid_dangerous_goods(cargo={"un_number":"1202","volume_m3":10}, vehicle={},
        tank={"total_volume_m3":30,"allowed_un_numbers":["UN1993"],"pump":False})
    assert result["result"] == "blocked"

def test_capacity_exceeded_is_blocked():
    result = check_liquid_dangerous_goods(cargo={"un_number":"1202","volume_m3":40}, vehicle={},
        tank={"total_volume_m3":30,"allowed_un_numbers":["1202"],"pump":False})
    assert result["result"] == "blocked"
