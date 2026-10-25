"""Out Patient Services — simple Sudha booking flow."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import GlobalPayload, OPDPayload, OPD_CONCERN_MAP, OPD_TRIMESTER_MAP
from handlers.common_booking import (
    ask_name_age,
    date_selection_response,
    handle_date_selection,
    handle_time_and_book,
    parse_name_age,
)
from state_machine import Session, SubState


def start_opd_prompt() -> Dict[str, Any]:
    return _concern_menu()


def handle_opd_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False,
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    if message in {OPDPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL}:
        return {"text": "Cancelled.", "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}]}, True, None

    sub = session.sub_state

    if sub == SubState.SELECT_CONCERN.value:
        return _select_concern(session, message, is_button)

    if sub == SubState.SELECT_TRIMESTER.value:
        return _select_trimester(session, message, is_button)

    if sub == SubState.ENTER_HUSBAND_NAME.value:
        if is_button:
            return {"text": "Type *Husband Name, Years married*\nExample: `Ravi, 3`"}, False, None
        name, years, err = parse_name_age(message)
        if err:
            return {"text": "Type *Husband Name, Years married*\nExample: `Ravi, 3`"}, False, None
        session.set_context("husband_name", name)
        session.set_context("years_married", years)
        session.set_sub_state(SubState.ENTER_NAME)
        return ask_name_age("✅ Couple details saved"), False, None

    if sub == SubState.ENTER_NAME.value:
        if is_button:
            return ask_name_age(), False, None
        name, age, err = parse_name_age(message)
        if err:
            return {"text": err}, False, None
        session.set_context("patient_name", name)
        session.set_context("age", age)
        session.set_sub_state(SubState.SELECT_DATE)
        return date_selection_response(f"✅ {name}, {age} yrs\n\nSelect appointment date:"), False, None

    if sub == SubState.SELECT_DATE.value:
        return (*handle_date_selection(session, message, clinic, is_button), None)

    if sub == SubState.SELECT_TIME.value:
        return handle_time_and_book(session, message, clinic, clinic_id, is_button, prefix="OPD")

    session.set_sub_state(SubState.SELECT_CONCERN)
    return _concern_menu(), False, None


def _concern_menu(intro: str = None) -> Dict[str, Any]:
    return {
        "text": intro or "*Out Patient*\n\nWhat is your concern?",
        "list": {
            "button_text": "Select Concern",
            "sections": [
                {
                    "title": "Concerns",
                    "rows": [
                        {"id": OPDPayload.CONCERN_PREGNANCY, "title": "Pregnancy", "description": "Antenatal care"},
                        {"id": OPDPayload.CONCERN_POST_DELIVERY, "title": "Post Delivery Care", "description": "After delivery"},
                        {"id": OPDPayload.CONCERN_MENSTRUAL, "title": "Menstrual Problems", "description": "Period concerns"},
                        {"id": OPDPayload.CONCERN_INFERTILITY, "title": "Infertility", "description": "Fertility care"},
                        {"id": OPDPayload.CONCERN_MENOPAUSE, "title": "Menopause", "description": "Menopause care"},
                        {"id": OPDPayload.CONCERN_CANCER, "title": "Cancer Screening", "description": "Screening checkup"},
                        {"id": OPDPayload.CONCERN_WELLNESS, "title": "Wellness Checkup", "description": "General wellness"},
                    ],
                }
            ],
        },
    }


def _select_concern(session: Session, message: str, is_button: bool):
    if not is_button or message not in OPD_CONCERN_MAP:
        return _concern_menu("Please select a concern:"), False, None

    concern = OPD_CONCERN_MAP[message]
    session.set_context("concern", concern["name"])
    session.set_context("service", concern["name"])
    session.set_context("service_type", f"opd_{concern['id']}")
    session.set_context("department", "Out Patient Services")

    # Pregnancy already selected — no second "are you pregnant?" question
    if concern["id"] == "pregnancy":
        session.set_context("is_pregnant", "Yes")
        session.set_sub_state(SubState.SELECT_TRIMESTER)
        return {
            "text": "Which trimester?",
            "buttons": [
                {"id": OPDPayload.TRIMESTER_1, "title": "First"},
                {"id": OPDPayload.TRIMESTER_2, "title": "Second"},
                {"id": OPDPayload.TRIMESTER_3, "title": "Third"},
            ],
        }, False, None

    if concern["id"] == "infertility":
        session.set_sub_state(SubState.ENTER_HUSBAND_NAME)
        return {"text": "Type *Husband Name, Years married*\nExample: `Ravi, 3`"}, False, None

    # All other concerns → name + age → date → time
    session.set_sub_state(SubState.ENTER_NAME)
    return ask_name_age(f"✅ {concern['name']}"), False, None


def _select_trimester(session: Session, message: str, is_button: bool):
    if not is_button or message not in OPD_TRIMESTER_MAP:
        return {
            "text": "Which trimester?",
            "buttons": [
                {"id": OPDPayload.TRIMESTER_1, "title": "First"},
                {"id": OPDPayload.TRIMESTER_2, "title": "Second"},
                {"id": OPDPayload.TRIMESTER_3, "title": "Third"},
            ],
        }, False, None
    session.set_context("trimester", OPD_TRIMESTER_MAP[message])
    session.set_sub_state(SubState.ENTER_NAME)
    return ask_name_age(f"✅ {OPD_TRIMESTER_MAP[message]}"), False, None
