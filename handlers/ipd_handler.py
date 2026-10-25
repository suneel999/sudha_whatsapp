"""In Patient / Admission — simple surgery enquiry + reception contact."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import (
    GlobalPayload,
    IPDPayload,
    IPD_GYNE_SURGERY_MAP,
    IPD_MENU_MAP,
    IPD_OBSTETRIC_SURGERY_MAP,
    IPD_SURGERY_GROUP_MAP,
    IPD_SURGERY_MAP,
)
from database import notify_staff, save_enquiry
from handlers.common_booking import generate_booking_id, validate_name
from state_machine import Session, SubState

RECEPTION_TEL = "tel:+918143800624"
RECEPTION_DISPLAY = "+91 81438 00624"


def start_ipd_prompt() -> Dict[str, Any]:
    return {
        "text": "*In Patient / Admission*\n\nHow can we help?",
        "list": {
            "button_text": "Select Option",
            "sections": [
                {
                    "title": "Options",
                    "rows": [
                        {
                            "id": IPDPayload.ADMISSION,
                            "title": "Admission / Surgery",
                            "description": "Select surgery & send enquiry",
                        },
                        {
                            "id": IPDPayload.RECEPTION,
                            "title": "Contact Reception",
                            "description": RECEPTION_DISPLAY,
                        },
                    ],
                }
            ],
        },
    }


def _surgery_group_menu() -> Dict[str, Any]:
    return {
        "text": "Which surgery do you need?\n\nSelect a group:",
        "buttons": [
            {"id": IPDPayload.SURG_GROUP_OBSTETRIC, "title": "Obstetric"},
            {"id": IPDPayload.SURG_GROUP_GYNE, "title": "Gynecological"},
        ],
    }


def _surgery_list(group_id: str) -> Dict[str, Any]:
    if group_id == "obstetric":
        surgery_map = IPD_OBSTETRIC_SURGERY_MAP
        title = "Obstetric surgeries"
    else:
        surgery_map = IPD_GYNE_SURGERY_MAP
        title = "Gynecological surgeries"
    return {
        "text": f"*{title}*\n\nWhich surgery do you need?",
        "list": {
            "button_text": "Select Surgery",
            "sections": [
                {
                    "title": "Surgeries",
                    "rows": [
                        {
                            "id": pid,
                            "title": meta["name"][:24],
                            "description": "Tap to continue",
                        }
                        for pid, meta in surgery_map.items()
                    ],
                }
            ],
        },
    }


def _reception_reply(clinic: dict) -> Dict[str, Any]:
    phone = clinic.get("reception_phone") or clinic.get("phone") or RECEPTION_DISPLAY
    return {
        "text": (
            "📞 *Call Reception*\n\n"
            f"Tap to call: {RECEPTION_TEL}\n"
            f"Number: *{phone}*\n\n"
            "Our front office will help you with admission."
        ),
        "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
    }


def handle_ipd_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False,
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    if message in {IPDPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL}:
        return {"text": "Cancelled.", "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}]}, True, None

    sub = session.sub_state

    if sub == SubState.SELECT_ENQUIRY.value:
        if not is_button:
            return start_ipd_prompt(), False, None

        if message == IPDPayload.RECEPTION:
            notify_staff(
                title="Reception Call Request",
                message=f"Patient asked to contact reception. WA: {session.user_id}",
                category="ipd_reception",
                reference_id="reception",
                user_id=session.user_id,
                payload={"type": "reception", "phone": RECEPTION_DISPLAY},
            )
            return _reception_reply(clinic), True, None

        if message == IPDPayload.ADMISSION:
            session.set_context("enquiry_type", "Admission / Surgery")
            session.set_sub_state(SubState.SELECT_SURGERY_GROUP)
            return _surgery_group_menu(), False, None

        # Legacy options → guide to new menu
        if message in {IPDPayload.ROOM, IPDPayload.INSURANCE, IPDPayload.BILLING}:
            return start_ipd_prompt(), False, None

        if message in IPD_MENU_MAP:
            session.set_context("enquiry_type", IPD_MENU_MAP[message]["name"])
            session.set_sub_state(SubState.ENTER_NAME)
            return {"text": "Type your *Name*:"}, False, None

        return start_ipd_prompt(), False, None

    if sub == SubState.SELECT_SURGERY_GROUP.value:
        if not is_button or message not in IPD_SURGERY_GROUP_MAP:
            return _surgery_group_menu(), False, None
        group = IPD_SURGERY_GROUP_MAP[message]
        session.set_context("surgery_group", group["name"])
        session.set_sub_state(SubState.SELECT_SURGERY)
        return _surgery_list(group["id"]), False, None

    if sub == SubState.SELECT_SURGERY.value:
        if not is_button or message not in IPD_SURGERY_MAP:
            group_id = "obstetric" if session.get_context("surgery_group") == "Obstetric" else "gynecological"
            return _surgery_list(group_id), False, None
        surgery = IPD_SURGERY_MAP[message]
        session.set_context("surgery", surgery["name"])
        session.set_context("enquiry_type", f"Admission — {surgery['name']}")
        session.set_context("service", surgery["name"])
        session.set_sub_state(SubState.ENTER_NAME)
        return {"text": f"✅ {surgery['name']}\n\nType your *Name*:"}, False, None

    if sub == SubState.ENTER_NAME.value:
        if is_button:
            return {"text": "Type your name:"}, False, None
        err = validate_name(message)
        if err:
            return {"text": err}, False, None

        phone_digits = "".join(ch for ch in session.user_id if ch.isdigit())
        phone = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        session.set_context("patient_name", message.strip())
        session.set_context("phone", phone)

        enquiry_id = generate_booking_id("IPD")
        notes = session.get_context("surgery") or session.get_context("enquiry_type")
        save_enquiry(
            enquiry_id=enquiry_id,
            user_id=session.user_id,
            patient_name=session.get_context("patient_name"),
            phone=phone,
            hospital_id=None,
            enquiry_type=session.get_context("enquiry_type"),
            department="In Patient Services",
            notes=notes,
        )
        notify_staff(
            title="IPD Admission Enquiry",
            message=(
                f"{session.get_context('enquiry_type')} | "
                f"{session.get_context('patient_name')} ({phone}). Ref: {enquiry_id}"
            ),
            category="ipd_enquiry",
            reference_id=enquiry_id,
            user_id=session.user_id,
            payload={
                "enquiry_type": session.get_context("enquiry_type"),
                "surgery": session.get_context("surgery"),
                "patient_name": session.get_context("patient_name"),
                "phone": phone,
                "reception": RECEPTION_DISPLAY,
            },
        )
        reception = clinic.get("reception_phone") or RECEPTION_DISPLAY
        return {
            "text": (
                f"✅ Enquiry sent to admission desk.\n\n"
                f"🆔 *{enquiry_id}*\n"
                f"📋 {session.get_context('enquiry_type')}\n"
                f"👤 {session.get_context('patient_name')}\n"
                f"📱 {phone}\n\n"
                f"We will call you shortly.\n"
                f"📞 Reception: *{reception}*\n"
                f"{RECEPTION_TEL}"
            ),
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True, None

    session.set_sub_state(SubState.SELECT_ENQUIRY)
    return start_ipd_prompt(), False, None
