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
    PharmacyPayload,
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

    print("2) Easy OPD pregnancy")
    route_message(user, MainMenuPayload.OPD, is_button_click=True)
    route_message(user, OPDPayload.CONCERN_PREGNANCY, is_button_click=True)
    route_message(user, OPDPayload.PREGNANT_YES, is_button_click=True)
    route_message(user, OPDPayload.TRIMESTER_2, is_button_click=True)
    route_message(user, "Anitha, 28")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "OPD auto-book failed")

    with get_connection() as conn:
        assert_true(conn.execute("SELECT COUNT(*) AS c FROM appointments").fetchone()["c"] >= 1, "No appointment")
        assert_true(conn.execute("SELECT COUNT(*) AS c FROM staff_notifications").fetchone()["c"] >= 1, "No notify")

    print("3) Easy ultrasound")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.ULTRASOUND, is_button_click=True)
    route_message(user, UltrasoundPayload.NON_PREGNANT, is_button_click=True)
    route_message(user, UltrasoundPayload.SCAN_PELVIS, is_button_click=True)
    route_message(user, "Sita, 32")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "US failed")

    print("4) Easy lab")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.LAB, is_button_click=True)
    route_message(user, LabPayload.TEST_THYROID, is_button_click=True)
    route_message(user, "Ravi, 40")
    route_message(user, f"{DATE_PREFIX}{date_id}", is_button_click=True)
    resp = route_message(user, f"{TIME_PREFIX}{time_id}", is_button_click=True)
    assert_true("booked successfully" in text_of(resp).lower(), "Lab failed")

    print("5) Pharmacy contact")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.PHARMACY, is_button_click=True)
    resp = route_message(user, PharmacyPayload.CONTACT, is_button_click=True)
    assert_true("request sent" in text_of(resp).lower() or "call" in text_of(resp).lower(), "Pharmacy failed")

    print("6) Prescription upload")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.PHARMACY, is_button_click=True)
    route_message(user, PharmacyPayload.UPLOAD, is_button_click=True)
    resp = route_message(user, "__MEDIA__", media={"media_id": "media_test_123"})
    assert_true("prescription received" in text_of(resp).lower(), "Rx failed")

    print("7) Easy IPD")
    route_message(user, GlobalPayload.MAIN_MENU, is_button_click=True)
    route_message(user, MainMenuPayload.IPD, is_button_click=True)
    route_message(user, IPDPayload.ROOM, is_button_click=True)
    resp = route_message(user, "Lakshmi")
    assert_true("enquiry sent" in text_of(resp).lower() or "staff" in text_of(resp).lower(), "IPD failed")

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
