"""
Shared appointment helpers — simplified Sudha booking (auto-book on time select).
"""

import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from button_payloads import BookingPayload, GlobalPayload, MainMenuPayload
from database import cancel_appointment as db_cancel_appointment
from database import notify_staff, save_appointment, update_appointment_slot
from state_machine import Session, SubState

logger = logging.getLogger(__name__)

DATE_PREFIX = "DATE_"
TIME_PREFIX = "TIME_"


def generate_booking_id(prefix: str = "SH") -> str:
    stamp = datetime.now().strftime("%m%d")
    rand = "".join(random.choices(string.digits, k=4))
    return f"{prefix}{stamp}{rand}"


def get_available_dates(limit: int = 7) -> List[dict]:
    dates = []
    current = datetime.now() + timedelta(days=1)
    while len(dates) < limit:
        if current.weekday() != 6:
            dates.append(
                {
                    "id": current.strftime("%Y-%m-%d"),
                    "display": current.strftime("%d %b"),
                    "day": current.strftime("%A"),
                }
            )
        current += timedelta(days=1)
    return dates


def get_time_slots(clinic: dict = None) -> List[dict]:
    slots = (clinic or {}).get(
        "time_slots",
        ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"],
    )
    # Keep short list for easy picking
    preferred = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
    use = [s for s in preferred if s in slots] or slots[:6]
    return [{"id": s.replace(":", "_").replace(" ", "_"), "display": s} for s in use]


def date_selection_response(intro: str = None) -> Dict[str, Any]:
    dates = get_available_dates()
    body = intro or "Select a date:"
    return {
        "text": body,
        "list": {
            "button_text": "Select Date",
            "sections": [
                {
                    "title": "Dates",
                    "rows": [
                        {
                            "id": f"{DATE_PREFIX}{d['id']}",
                            "title": d["display"][:24],
                            "description": d["day"],
                        }
                        for d in dates
                    ],
                }
            ],
        },
    }


def time_selection_response(date_str: str, clinic: dict = None, intro: str = None) -> Dict[str, Any]:
    slots = get_time_slots(clinic)
    body = intro or f"Date: *{date_str}*\n\nSelect a time:"
    return {
        "text": body,
        "list": {
            "button_text": "Select Time",
            "sections": [
                {
                    "title": "Time Slots",
                    "rows": [
                        {"id": f"{TIME_PREFIX}{s['id']}", "title": s["display"], "description": "Tap to book"}
                        for s in slots
                    ],
                }
            ],
        },
    }


def handle_date_selection(session: Session, message: str, clinic: dict, is_button: bool) -> Tuple[Dict[str, Any], bool]:
    if not is_button or not message.startswith(DATE_PREFIX):
        return date_selection_response("Please select a date:"), False
    date_str = message.replace(DATE_PREFIX, "", 1)
    session.set_context("date", date_str)
    session.set_sub_state(SubState.SELECT_TIME)
    return time_selection_response(date_str, clinic), False


def _slot_display(slot_id: str) -> str:
    parts = slot_id.split("_")
    if len(parts) >= 3:
        return f"{parts[0]}:{parts[1]} {parts[2]}"
    return slot_id.replace("_", " ")


def finalize_booking(
    session: Session,
    clinic: dict,
    clinic_id: str,
    prefix: str = "SH",
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    """Save booking immediately and return success message."""
    ctx = session.context
    booking_id = generate_booking_id(prefix)
    notes = build_notes(ctx)
    saved = save_appointment(
        booking_id=booking_id,
        user_id=session.user_id,
        patient_name=ctx.get("patient_name", "Patient"),
        department=ctx.get("department_id", ctx.get("department", "")),
        department_name=ctx.get("department", ""),
        doctor=ctx.get("doctor_reference") or ctx.get("service", ""),
        date=ctx.get("date"),
        time_slot=ctx.get("time"),
        clinic_id=clinic_id or "default",
        service_type=ctx.get("service_type", "appointment"),
        phone=session.user_id,
        notes=notes,
    )
    if not saved:
        return {
            "text": "❌ Booking failed. Please try again or call reception.",
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True, None

    notify_staff(
        title="New Appointment Booked",
        message=(
            f"{ctx.get('patient_name')} | {ctx.get('department')} | "
            f"{ctx.get('service')} | {ctx.get('date')} {ctx.get('time')} | Ref: {booking_id}"
        ),
        category="appointment",
        reference_id=booking_id,
        user_id=session.user_id,
        payload={
            "booking_id": booking_id,
            "patient_name": ctx.get("patient_name"),
            "department": ctx.get("department"),
            "service": ctx.get("service"),
            "date": ctx.get("date"),
            "time": ctx.get("time"),
            "notes": notes,
        },
    )

    booking_ctx = {
        "booking_id": booking_id,
        "patient_name": ctx.get("patient_name"),
        "department": ctx.get("department"),
        "service": ctx.get("service"),
        "date": ctx.get("date"),
        "time": ctx.get("time"),
        "service_type": ctx.get("service_type", "appointment"),
    }
    return success_message(booking_ctx, clinic), True, booking_ctx


def handle_time_and_book(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool,
    prefix: str = "SH",
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    """Selecting time immediately books the appointment (no confirm step)."""
    if not is_button or not message.startswith(TIME_PREFIX):
        return time_selection_response(session.get_context("date", ""), clinic, "Please select a time:"), False, None
    slot_id = message.replace(TIME_PREFIX, "", 1)
    session.set_context("time", _slot_display(slot_id))
    return finalize_booking(session, clinic, clinic_id, prefix=prefix)


def build_notes(ctx: Dict[str, Any]) -> str:
    keys = [
        "marital_status",
        "concern",
        "is_pregnant",
        "trimester",
        "lmp",
        "symptoms",
        "husband_name",
        "husband_age",
        "years_married",
        "scan_type",
        "weeks_pregnant",
        "doctor_reference",
        "lab_test",
        "enquiry_type",
        "hospital_id",
    ]
    payload = {k: ctx[k] for k in keys if ctx.get(k) not in (None, "", [])}
    return json.dumps(payload, ensure_ascii=True)


def success_message(booking_ctx: Dict[str, Any], clinic: dict) -> Dict[str, Any]:
    return {
        "text": (
            f"✅ *Booked successfully!*\n\n"
            f"👤 {booking_ctx.get('patient_name')}\n"
            f"🩺 {booking_ctx.get('service')}\n"
            f"📅 {booking_ctx.get('date')}  ⏰ {booking_ctx.get('time')}\n"
            f"🆔 *{booking_ctx.get('booking_id')}*\n\n"
            f"📞 {clinic.get('phone', '')}"
        ),
        "buttons": [
            {"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"},
            {"id": BookingPayload.CANCEL, "title": "❌ Cancel"},
        ],
    }


def post_booking_confirmation(booking_ctx: Dict[str, Any], clinic: dict) -> Dict[str, Any]:
    return success_message(booking_ctx, clinic)


def handle_post_booking(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool,
) -> Tuple[Dict[str, Any], bool]:
    booking_id = session.get_context("booking_id")

    if message == GlobalPayload.MAIN_MENU:
        return {"text": "Main menu", "buttons": []}, True

    if message == BookingPayload.CANCEL or message == BookingPayload.CONFIRM_CANCEL_YES:
        db_cancel_appointment(booking_id, cancelled_by="patient", cancel_reason="Cancelled via WhatsApp")
        notify_staff(
            title="Appointment Cancelled",
            message=f"Ref {booking_id} cancelled by patient {session.get_context('patient_name')}",
            category="appointment_cancel",
            reference_id=booking_id,
            user_id=session.user_id,
        )
        return {
            "text": f"✅ Appointment *{booking_id}* cancelled.",
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True

    if message == BookingPayload.MODIFY:
        session.set_sub_state(SubState.SELECT_DATE)
        return date_selection_response(f"Change date for *{booking_id}*:"), False

    if session.sub_state == SubState.SELECT_DATE.value:
        if not is_button or not message.startswith(DATE_PREFIX):
            return date_selection_response("Select a new date:"), False
        date_str = message.replace(DATE_PREFIX, "", 1)
        session.set_context("date", date_str)
        session.set_sub_state(SubState.SELECT_TIME)
        return time_selection_response(date_str, clinic, "Select a new time:"), False

    if session.sub_state == SubState.SELECT_TIME.value:
        if not is_button or not message.startswith(TIME_PREFIX):
            return time_selection_response(session.get_context("date", ""), clinic), False
        display = _slot_display(message.replace(TIME_PREFIX, "", 1))
        session.set_context("time", display)
        update_appointment_slot(booking_id, session.get_context("date"), display)
        notify_staff(
            title="Appointment Modified",
            message=f"Ref {booking_id} → {session.get_context('date')} {display}",
            category="appointment_modify",
            reference_id=booking_id,
            user_id=session.user_id,
        )
        session.set_sub_state(SubState.POST_CONFIRM)
        return success_message(session.context, clinic), False

    return success_message(session.context, clinic), False


def main_menu_list(intro: str = None) -> Dict[str, Any]:
    body = intro or "👋 Welcome to *Sudha Hospital*.\n\nPlease choose a service."
    return {
        "text": body,
        "list": {
            "button_text": "Choose Service",
            "sections": [
                {
                    "title": "Services",
                    "rows": [
                        {"id": MainMenuPayload.OPD, "title": "Out Patient", "description": "Consultation booking"},
                        {"id": MainMenuPayload.ULTRASOUND, "title": "Ultrasound", "description": "Scan booking"},
                        {"id": MainMenuPayload.LAB, "title": "Lab Services", "description": "Lab test booking"},
                        {"id": MainMenuPayload.PHARMACY, "title": "Pharmacy", "description": "Medicines & prescription"},
                        {"id": MainMenuPayload.IPD, "title": "In Patient", "description": "Admission & billing help"},
                    ],
                }
            ],
        },
    }


def validate_name(name: str) -> Optional[str]:
    name = (name or "").strip()
    if len(name) < 2:
        return "❌ Please enter a valid name:"
    if len(name) > 100:
        return "❌ Name too long. Try again:"
    if any(ch.isdigit() for ch in name):
        return "❌ Name should not have numbers. Try again:"
    return None


def validate_age(age_text: str) -> Optional[str]:
    age_text = (age_text or "").strip()
    if not age_text.isdigit():
        return "❌ Enter age as a number (example: 28):"
    age = int(age_text)
    if age < 1 or age > 120:
        return "❌ Enter a valid age (1-120):"
    return None


def parse_name_age(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse 'Name, Age' or 'Name Age'.
    Returns (name, age, error_message).
    """
    text = (text or "").strip()
    if "," in text:
        parts = [p.strip() for p in text.split(",", 1)]
    else:
        tokens = text.rsplit(" ", 1)
        parts = tokens if len(tokens) == 2 and tokens[1].isdigit() else [text, ""]

    if len(parts) < 2 or not parts[1]:
        return None, None, "Type *Name, Age*\nExample: `Anitha, 28`"

    name, age = parts[0].strip(), parts[1].strip()
    err = validate_name(name)
    if err:
        return None, None, err
    err = validate_age(age)
    if err:
        return None, None, err
    return name, age, None


def ask_name_age(intro: str = None) -> Dict[str, Any]:
    return {
        "text": (intro or "Enter patient details") + "\n\nType *Name, Age*\nExample: `Anitha, 28`"
    }


def parse_date_text(text: str) -> Optional[str]:
    text = (text or "").strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# Back-compat aliases used by older handler imports
def handle_time_selection(session, message, clinic, is_button, confirm_yes=None, confirm_no=None):
    """Legacy signature — prefer handle_time_and_book."""
    if not is_button or not message.startswith(TIME_PREFIX):
        return time_selection_response(session.get_context("date", ""), clinic), False
    session.set_context("time", _slot_display(message.replace(TIME_PREFIX, "", 1)))
    session.set_sub_state(SubState.CONFIRM)
    return {
        "text": "Tap Confirm to book:",
        "buttons": [
            {"id": confirm_yes or "CONFIRM_YES", "title": "✅ Confirm"},
            {"id": confirm_no or "CONFIRM_NO", "title": "❌ Cancel"},
        ],
    }, False


def save_and_confirm_appointment(session, clinic, clinic_id, confirm_yes, confirm_no, message, is_button, prefix="SH"):
    """Legacy confirm handler — now books on yes, or immediately if already timed."""
    if not is_button:
        lower = message.lower().strip()
        if lower in {"yes", "y", "confirm", "ok"}:
            message = confirm_yes
        elif lower in {"no", "n", "cancel"}:
            message = confirm_no
    if message == confirm_no:
        return {
            "text": "Cancelled.",
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }, True, None
    if message == confirm_yes or (session.get_context("date") and session.get_context("time")):
        return finalize_booking(session, clinic, clinic_id, prefix=prefix)
    return handle_time_and_book(session, message, clinic, clinic_id, is_button, prefix)
