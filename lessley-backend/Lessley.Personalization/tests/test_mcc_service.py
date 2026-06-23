"""MCC-code category tags must resolve to category name strings."""

from services.mcc_service import MccService


def _service():
    svc = MccService()
    svc._mcc_map = {
        "5411": "GROCERY STORES, SUPERMARKETS",
        "5812": "EATING PLACES, RESTAURANTS",
    }
    return svc


def test_category_name_tag_resolves_to_itself():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("GROCERY STORES, SUPERMARKETS") == ["GROCERY STORES, SUPERMARKETS"]


def test_legacy_numeric_tag_resolves_to_category_name():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("5411") == ["GROCERY STORES, SUPERMARKETS"]
    assert svc.get_mcc_codes_by_tag(" 5812 ") == ["EATING PLACES, RESTAURANTS"]


def test_unknown_tag_returns_empty():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("9999") == []
    assert svc.get_mcc_codes_by_tag("") == []
