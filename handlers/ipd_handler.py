"""In Patient Services — simplified Sudha flow."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import GlobalPayload, IPD_ENQUIRY_MAP, IPDPayload
from database import notify_staff, save_enquiry
from handlers.common_booking import generate_booking_id, validate_name
from state_machine import Session, SubState


def start_ipd_prompt() -> Dict[str, Any]:
    return {
        "text": "*In Patient*\n\nHow can we help?",
        "list": {
            "button_text": "Select Option",
            "sections": [
                {
                    "title": "Options",
                    "rows": [
                        {"id": pid, "title": meta["name"][:24], "description": "Send enquiry to staff"}
                        for pid, meta in IPD_ENQUIRY_MAP.items()
                    ],
                }
            ],
        },
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
        if not is_button or message not in IPD_ENQUIRY_MAP:
            return start_ipd_prompt(), False, None
        enquiry = IPD_ENQUIRY_MAP[message]
        session.set_context("enquiry_type", enquiry["name"])
        session.set_context("service", enquiry["name"])
        session.set_sub_state(SubState.ENTER_NAME)
        return {"text": f"✅ {enquiry['name']}\n\nType your *Name*:"}, False, None

    if sub == SubState.ENTER_NAME.value:
        if is_button:
            return {"text": "Type your name:"}, False, None
        err = validate_name(message)
        if err:
            return {"text": err}, False, None

        # Auto-use WhatsApp number; skip hospital ID
        phone_digits = "".join(ch for ch in session.user_id if ch.isdigit())
        phone = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        session.set_context("patient_name", message.strip())
        session.set_context("phone", phone)

        enquiry_id = generate_booking_id("IPD")
        save_enquiry(
            enquiry_id=enquiry_id,
            user_id=session.user_id,
            patient_name=session.get_context("patient_name"),
            phone=phone,
            hospital_id=None,
            enquiry_type=session.get_context("enquiry_type"),
            department="In Patient Services",
        )
        notify_staff(
            title="IPD Enquiry",
            message=(
                f"{session.get_context('enquiry_type')} from "
                f"{session.get_context('patient_name')} ({phone}). Ref: {enquiry_id}"
            ),
            category="ipd_enquiry",
            reference_id=enquiry_id,
            user_id=session.user_id,
            payload={
                "enquiry_type": session.get_context("enquiry_type"),
                "patient_name": session.get_context("patient_name"),
                "phone": phone,
            },
        )
        return {
            "text": (
                f"✅ Enquiry sent to staff.\n\n"
                f"🆔 *{enquiry_id}*\n"
                f"📋 {session.get_context('enquiry_type')}\n"
                f"👤 {session.get_context('patient_name')}\n"
                f"📱 {phone}\n\n"
                f"We will call you shortly.\n📞 {clinic.get('phone', '')}"
            ),
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True, None

    session.set_sub_state(SubState.SELECT_ENQUIRY)
    return start_ipd_prompt(), False, None
