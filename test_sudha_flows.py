"""Smoke tests for simplified Sudha flows."""

import os
import sys

os.environ["TESTING"] = "1"
TEST_DB = "sudha_test.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import database

database.DATABASE_FILE = TEST_DB
database.init_database()

from button_payloads import (
    MainMenuPayload,
    OPDPayload,
    UltrasoundPayload,
    LabPayload,
    IPDPayload,
    GlobalPayload,
)
from message_router import route_message
from database import get_connection
from handlers.common_booking import get_available_dates, DATE_PREFIX, TIME_PREFIX, get_time_slots


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def text_of(resp):
    return resp.get("text", "") if isinstance(resp, dict) else str(resp or "")


def run():
    user = "919999000111"
    date_id = get_available_dates()[0]["id"]
    time_id = get_time_slots()[0]["id"]

    print("1) Main menu")
    resp = route_message(user, "hi")
    assert_true("Sudha Hospital" in text_of(resp), "Welcome missing")
    rows = resp.get("list", {}).get("sections", [{}])[0].get("rows", [])
    titles = [r["title"] for r in rows]
    assert_true("Location" in titles, "Location missing from menu")
    assert_true("About Hospital" in titles, "About missing from menu")
    assert_true("Pharmacy" not in titles, "Pharmacy should be removed")

    print("2) Location + About")
    resp = route_message(user, MainMenuPayload.LOCATION, is_button_click=True)
    assert_true("KPHB" in text_of(resp) or "Location" in text_of(resp) or "Sudha" in text_of(resp), "Location failed")
    resp = route_message(user, MainMenuPayload.ABOUT, is_button_click=True)
    assert_true("sudhahospitalkphb.com" in text_of(resp).lower(), "About URL missing")

    print("3) Easy OPD pregnancy (no second pregnant question)")
    route_message(user, MainMenuPayload.OPD, is_button_click=True)
    resp = route_message(user, OPDPayload.CONCERN_PREGNANCY, is_button_click=True)
    assert_true("trimester" in text_of(resp).lower(), "Should ask trimester directly")
    assert_true("are you currently pregnant" not in text_of(resp).lower(), "Should not re-ask pregnant")
    route_message(user, OPDPayload.TRIMESTER_2, is_button_click=True)
    route_message(user, "Anitha, 28")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "OPD auto-book failed")

    print("4) New OPD concerns")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.OPD, is_button_click=True)
    resp = route_message(user, OPDPayload.CONCERN_WELLNESS, is_button_click=True)
    assert_true("name" in text_of(resp).lower(), "Wellness should ask name")
    route_message(user, "Meena, 35")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "Wellness book failed")

    print("5) Easy ultrasound")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.ULTRASOUND, is_button_click=True)
    route_message(user, UltrasoundPayload.NON_PREGNANT, is_button_click=True)
    route_message(user, UltrasoundPayload.SCAN_PELVIS, is_button_click=True)
    route_message(user, "Sita, 32")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "US failed")

    print("6) Easy lab")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.LAB, is_button_click=True)
    route_message(user, LabPayload.TEST_THYROID, is_button_click=True)
    route_message(user, "Ravi, 40")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "Lab failed")

    print("7) Admission surgery flow")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.IPD, is_button_click=True)
    route_message(user, IPDPayload.ADMISSION, is_button_click=True)
    route_message(user, IPDPayload.SURG_GROUP_GYNE, is_button_click=True)
    route_message(user, IPDPayload.SURG_LAP_HYST, is_button_click=True)
    resp = route_message(user, "Lakshmi")
    assert_true("enquiry sent" in text_of(resp).lower() or "admission" in text_of(resp).lower(), "IPD failed")
    assert_true("81438" in text_of(resp), "Reception number missing")

    print("8) Contact reception")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.IPD, is_button_click=True)
    resp = route_message(user, IPDPayload.RECEPTION, is_button_click=True)
    assert_true("tel:+918143800624" in text_of(resp), "Reception tel missing")

    with get_connection() as conn:
        assert_true(conn.execute("SELECT COUNT(*) AS c FROM appointments").fetchone()["c"] >= 3, "Missing appointments")
        assert_true(conn.execute("SELECT COUNT(*) AS c FROM enquiries").fetchone()["c"] >= 1, "Missing enquiry")

    print("\nALL SIMPLIFIED FLOW TESTS PASSED")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("\nFAILED:", exc)
        sys.exit(1)
    finally:
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass
