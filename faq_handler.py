"""
FAQ Handler for Sudha Hospital
Keyword-based FAQ matching - rule-based, no AI.
"""

from typing import Dict, Optional, Tuple
from config import get_clinic_config


FAQ_KEYWORDS: Dict[Tuple[str, ...], str] = {
    ("address", "location", "where", "directions", "located", "reach", "map"): "address",
    ("hours", "timing", "timings", "open", "close", "working hours", "opd timing", "opd hours"): "hours",
    ("phone", "call", "contact", "number", "reception", "helpline"): "contact",
    ("fee", "fees", "cost", "price", "charge", "payment", "charges"): "fees",
    ("service", "services", "facilities", "opd", "ultrasound", "lab", "admission", "ipd"): "services",
    ("appointment", "book", "booking", "schedule"): "appointment",
    ("emergency", "urgent"): "emergency",
    ("about", "hospital", "sudha", "website"): "about",
}


def match_faq(message: str) -> Optional[Tuple[str, str]]:
    if not message:
        return None
    msg = message.lower().strip()
    clinic = get_clinic_config()
    responses = _build_responses(clinic)

    for keywords, key in FAQ_KEYWORDS.items():
        if any(k in msg for k in keywords):
            if key in responses:
                return key, responses[key]
    return None


def _build_responses(clinic: dict) -> Dict[str, str]:
    name = clinic.get("name", "Sudha Hospital")
    reception = clinic.get("reception_phone") or clinic.get("phone", "")
    reception_tel = clinic.get("reception_tel") or "tel:+918143800624"
    website = clinic.get("website") or "https://sudhahospitalkphb.com/"
    return {
        "address": (
            f"📍 *{name}*\n\n"
            f"{clinic.get('address', 'Sudha Hospital, KPHB, Hyderabad')}\n"
            f"🌐 {website}"
        ),
        "hours": f"🕒 *Hospital Hours*\n\n{clinic.get('hours', 'OPD: Mon-Sat 9AM-7PM')}",
        "contact": (
            f"📞 *Contact {name}*\n\n"
            f"Reception: {reception}\n"
            f"{reception_tel}\n"
            f"Email: {clinic.get('email', '')}"
        ),
        "fees": (
            f"💳 *Fees & Payment*\n\n"
            "Please contact reception for current consultation and test fees.\n"
            f"📞 {reception}\n{reception_tel}"
        ),
        "services": (
            f"🏥 *{name} Services*\n\n"
            "• Out Patient\n"
            "• Ultrasound\n"
            "• Lab Services\n"
            "• Location\n"
            "• About Hospital\n"
            "• Admission / Surgery\n\n"
            "Type *hi* to open the main menu and book."
        ),
        "appointment": (
            "✅ You can book via WhatsApp.\n\n"
            "Type *hi* and choose a service from the menu."
        ),
        "emergency": (
            f"🚑 For emergencies, please call immediately:\n"
            f"📞 {reception}\n"
            f"{reception_tel}"
        ),
        "about": (
            f"🏥 *About {name}*\n\n"
            f"Type: {clinic.get('type', 'Women & Multi-specialty Hospital')}\n\n"
            f"Visit: {website}"
        ),
    }


def get_welcome_message(clinic: dict = None) -> str:
    clinic = clinic or get_clinic_config()
    return f"👋 Welcome to *{clinic.get('name', 'Sudha Hospital')}*.\n\nPlease choose a service."
