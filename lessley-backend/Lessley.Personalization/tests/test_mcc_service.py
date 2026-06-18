"""Task 2 — MCC-code category tags must resolve to MCC codes."""

from services.mcc_service import MccService


def _service():
    svc = MccService()
    svc._mcc_map = {
        "5411": "GROCERY STORES, SUPERMARKETS",
        "5812": "EATING PLACES, RESTAURANTS",
    }
    return svc


def test_mcc_code_label_resolves_to_that_code():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("5411") == [5411]
    assert svc.get_mcc_codes_by_tag(" 5812 ") == [5812]


def test_full_description_still_resolves():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("GROCERY STORES, SUPERMARKETS") == [5411]


def test_unknown_tag_returns_empty():
    svc = _service()
    assert svc.get_mcc_codes_by_tag("9999") == []
    assert svc.get_mcc_codes_by_tag("") == []
