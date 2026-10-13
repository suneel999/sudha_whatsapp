"""Ultrasound Scanning — simplified Sudha flow."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import (
    GlobalPayload,
    UltrasoundPayload,
    US_NON_PREGNANT_SCAN_MAP,
    US_PREGNANT_SCAN_MAP,
)
from handlers.common_booking import (
    ask_name_age,
    date_selection_response,
    handle_date_selection,
    handle_time_and_book,
    parse_name_age,
)
from state_machine import Session, SubState


def start_ultrasound_prompt() -> Dict[str, Any]:
    return {
        "text": "*Ultrasound*\n\nWhich type?",
        "buttons": [
            {"id": UltrasoundPayload.PREGNANT, "title": "Pregnant"},
            {"id": UltrasoundPayload.NON_PREGNANT, "title": "Non Pregnant"},
        ],
    }


def handle_ultrasound_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False,
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    if message in {UltrasoundPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL}:
        return {"text": "Cancelled.", "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}]}, True, None

    sub = session.sub_state

    if sub == SubState.SELECT_US_TYPE.value:
        return _select_type(session, message, is_button)

    if sub == SubState.SELECT_SCAN.value:
        return _select_scan(session, message, is_button)

    if sub == SubState.ENTER_NAME.value:
        if is_button:
            return ask_name_age(), False, None
        name, age, err = parse_name_age(message)
        if err:
            return {"text": err}, False, None
        session.set_context("patient_name", name)
        session.set_context("age", age)
        if session.get_context("us_category") == "Pregnant":
            session.set_sub_state(SubState.ENTER_WEEKS)
            return {"text": "Weeks of pregnancy? (example: `12`)"}, False, None
        session.set_sub_state(SubState.SELECT_DATE)
        return date_selection_response(f"✅ {name}\n\nSelect date:"), False, None

    if sub == SubState.ENTER_WEEKS.value:
        if is_button:
            return {"text": "Type weeks (example: `12`):"}, False, None
        text = message.strip()
        if not text.isdigit() or not (1 <= int(text) <= 45):
            return {"text": "❌ Enter weeks as a number (1-45):"}, False, None
        session.set_context("weeks_pregnant", text)
        session.set_sub_state(SubState.SELECT_DATE)
        return date_selection_response(f"✅ {text} weeks\n\nSelect date:"), False, None

    if sub == SubState.SELECT_DATE.value:
        return (*handle_date_selection(session, message, clinic, is_button), None)

    if sub == SubState.SELECT_TIME.value:
        return handle_time_and_book(session, message, clinic, clinic_id, is_button, prefix="USG")

    session.set_sub_state(SubState.SELECT_US_TYPE)
    return start_ultrasound_prompt(), False, None


def _select_type(session: Session, message: str, is_button: bool):
    if not is_button or message not in {UltrasoundPayload.PREGNANT, UltrasoundPayload.NON_PREGNANT}:
        return start_ultrasound_prompt(), False, None

    if message == UltrasoundPayload.PREGNANT:
        session.set_context("us_category", "Pregnant")
        session.set_sub_state(SubState.SELECT_SCAN)
        return {
            "text": "Select scan:",
            "list": {
                "button_text": "Select Scan",
                "sections": [
                    {
                        "title": "Pregnant Scans",
                        "rows": [
                            {"id": pid, "title": meta["name"][:24], "description": "Ultrasound"}
                            for pid, meta in US_PREGNANT_SCAN_MAP.items()
                        ],
                    }
                ],
            },
        }, False, None

    session.set_context("us_category", "Non Pregnant")
    session.set_sub_state(SubState.SELECT_SCAN)
    return {
        "text": "Select scan:",
        "buttons": [
            {"id": UltrasoundPayload.SCAN_PELVIS, "title": "Pelvis Scan"},
            {"id": UltrasoundPayload.SCAN_ABD_PELVIS, "title": "Abd + Pelvis"},
            {"id": UltrasoundPayload.SCAN_FOLLICULAR, "title": "Follicular Study"},
        ],
    }, False, None


def _select_scan(session: Session, message: str, is_button: bool):
    category = session.get_context("us_category")
    mapping = US_PREGNANT_SCAN_MAP if category == "Pregnant" else US_NON_PREGNANT_SCAN_MAP
    if not is_button or message not in mapping:
        return start_ultrasound_prompt(), False, None

    scan = mapping[message]
    session.set_context("scan_type", scan["name"])
    session.set_context("service", scan["name"])
    session.set_context("service_type", f"ultrasound_{scan['id']}")
    session.set_context("department", "Ultrasound Scanning")
    session.set_sub_state(SubState.ENTER_NAME)
    return ask_name_age(f"✅ {scan['name']}"), False, None
