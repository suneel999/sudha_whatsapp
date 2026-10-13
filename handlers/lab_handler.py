"""Lab Services — simplified Sudha flow."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import GlobalPayload, LAB_TEST_MAP, LabPayload
from handlers.common_booking import (
    ask_name_age,
    date_selection_response,
    handle_date_selection,
    handle_time_and_book,
    parse_name_age,
)
from state_machine import Session, SubState


def start_lab_prompt() -> Dict[str, Any]:
    return _tests_menu()


def handle_lab_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False,
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    if message in {LabPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL}:
        return {"text": "Cancelled.", "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}]}, True, None

    sub = session.sub_state

    if sub == SubState.SELECT_TEST.value:
        if not is_button or message not in LAB_TEST_MAP:
            return _tests_menu("Select a test:"), False, None
        test = LAB_TEST_MAP[message]
        session.set_context("lab_test", test["name"])
        session.set_context("service", test["name"])
        session.set_context("service_type", f"lab_{test['id']}")
        session.set_context("department", "Lab Services")
        session.set_sub_state(SubState.ENTER_NAME)
        return ask_name_age(f"✅ {test['name']}"), False, None

    if sub == SubState.ENTER_NAME.value:
        if is_button:
            return ask_name_age(), False, None
        name, age, err = parse_name_age(message)
        if err:
            return {"text": err}, False, None
        session.set_context("patient_name", name)
        session.set_context("age", age)
        session.set_sub_state(SubState.SELECT_DATE)
        return date_selection_response(f"✅ {name}\n\nSelect date:"), False, None

    if sub == SubState.SELECT_DATE.value:
        return (*handle_date_selection(session, message, clinic, is_button), None)

    if sub == SubState.SELECT_TIME.value:
        return handle_time_and_book(session, message, clinic, clinic_id, is_button, prefix="LAB")

    session.set_sub_state(SubState.SELECT_TEST)
    return _tests_menu(), False, None


def _tests_menu(intro: str = None) -> Dict[str, Any]:
    return {
        "text": intro or "*Lab Services*\n\nSelect a test:",
        "list": {
            "button_text": "Select Test",
            "sections": [
                {
                    "title": "Tests",
                    "rows": [
                        {"id": pid, "title": meta["name"], "description": "Book lab test"}
                        for pid, meta in LAB_TEST_MAP.items()
                    ],
                }
            ],
        },
    }
