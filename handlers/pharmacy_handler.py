"""Pharmacy — simplified Sudha flow."""

from typing import Any, Dict, Optional, Tuple

from button_payloads import GlobalPayload, PharmacyPayload
from database import notify_staff, save_prescription
from handlers.common_booking import generate_booking_id
from state_machine import Session, SubState


def start_pharmacy_prompt() -> Dict[str, Any]:
    return {
        "text": "*Pharmacy*\n\nHow can we help?",
        "buttons": [
            {"id": PharmacyPayload.AVAILABILITY, "title": "Check Medicine"},
            {"id": PharmacyPayload.UPLOAD, "title": "Upload Rx"},
            {"id": PharmacyPayload.CONTACT, "title": "Call Pharmacist"},
        ],
    }


def handle_pharmacy_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False,
    media: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    if message in {PharmacyPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL}:
        return {"text": "Cancelled.", "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}]}, True, None

    sub = session.sub_state

    if sub == SubState.SELECT_PHARMACY_HELP.value:
        if not is_button:
            return start_pharmacy_prompt(), False, None

        if message == PharmacyPayload.AVAILABILITY:
            session.set_sub_state(SubState.ENTER_MEDICINE_NAME)
            return {"text": "Type the medicine name:"}, False, None

        if message == PharmacyPayload.UPLOAD:
            session.set_sub_state(SubState.WAIT_PRESCRIPTION_IMAGE)
            return {"text": "Please send a clear *photo* of your prescription."}, False, None

        if message == PharmacyPayload.CONTACT:
            request_id = generate_booking_id("PHC")
            notify_staff(
                title="Pharmacist Contact Request",
                message=f"Patient {session.user_id} wants pharmacist contact. Ref: {request_id}",
                category="pharmacy_contact",
                reference_id=request_id,
                user_id=session.user_id,
            )
            return {
                "text": f"✅ Request sent (*{request_id}*).\nWe will call you shortly.\n📞 {clinic.get('phone', '')}",
                "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
            }, True, None

        return start_pharmacy_prompt(), False, None

    if sub == SubState.ENTER_MEDICINE_NAME.value:
        if is_button:
            return {"text": "Type the medicine name:"}, False, None
        medicine = message.strip()
        if len(medicine) < 2:
            return {"text": "Please type a valid medicine name:"}, False, None
        request_id = generate_booking_id("MED")
        notify_staff(
            title="Medicine Availability Check",
            message=f"Check '{medicine}' for {session.user_id}. Ref: {request_id}",
            category="pharmacy_availability",
            reference_id=request_id,
            user_id=session.user_id,
            payload={"medicine": medicine},
        )
        return {
            "text": f"✅ Checking *{medicine}*.\nRef: *{request_id}*\nStaff will reply shortly.",
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True, None

    if sub == SubState.WAIT_PRESCRIPTION_IMAGE.value:
        if media and media.get("media_id"):
            request_id = generate_booking_id("RX")
            save_prescription(
                request_id=request_id,
                user_id=session.user_id,
                media_id=media.get("media_id"),
                media_url=media.get("media_url"),
                local_path=media.get("local_path"),
                notes="Prescription uploaded via WhatsApp",
            )
            notify_staff(
                title="Prescription Uploaded",
                message=f"Prescription from {session.user_id}. Ref: {request_id}",
                category="pharmacy_prescription",
                reference_id=request_id,
                user_id=session.user_id,
                payload={"media_id": media.get("media_id")},
            )
            return {
                "text": f"✅ Prescription received.\nRef: *{request_id}*\nPharmacy notified.",
                "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
            }, True, None

        return {
            "text": "Please send a prescription *photo*.",
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, False, None

    session.set_sub_state(SubState.SELECT_PHARMACY_HELP)
    return start_pharmacy_prompt(), False, None
