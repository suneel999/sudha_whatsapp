"""
FAQ Handler for Sudha Hospital
Keyword-based FAQ matching - rule-based, no AI.
"""

from typing import Dict, Optional, Tuple
from config import get_clinic_config


FAQ_KEYWORDS: Dict[Tuple[str, ...], str] = {
    ("address", "location", "where", "directions", "located", "reach"): "address",
    ("hours", "timing", "timings", "open", "close", "working hours", "opd timing", "opd hours"): "hours",
    ("phone", "call", "contact", "number", "reception", "helpline"): "contact",
    ("fee", "fees", "cost", "price", "charge", "payment", "charges"): "fees",
    ("service", "services", "facilities", "opd", "ultrasound", "lab", "pharmacy", "ipd"): "services",
    ("appointment", "book", "booking", "schedule"): "appointment",
    ("emergency", "urgent"): "emergency",
    ("about", "hospital", "sudha"): "about",
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
    return {
        "address": f"📍 *{name}*\n\n{clinic.get('address', 'Sudha Hospital')}\n🌐 {clinic.get('website', '')}",
        "hours": f"🕒 *Hospital Hours*\n\n{clinic.get('hours', 'OPD: Mon-Sat 9AM-7PM')}",
        "contact": (
            f"📞 *Contact {name}*\n\n"
            f"Reception: {clinic.get('phone', '')}\n"
            f"Alternate: {clinic.get('alternate_phone', '')}\n"
            f"Email: {clinic.get('email', '')}"
        ),
        "fees": (
            f"💳 *Fees & Payment*\n\n"
            "Please contact reception for current consultation and test fees.\n"
            f"📞 {clinic.get('phone', '')}"
        ),
        "services": (
            f"🏥 *{name} Services*\n\n"
            "• Out Patient Services\n"
            "• Ultrasound Scanning\n"
            "• Lab Services\n"
            "• Pharmacy\n"
            "• In Patient Services\n\n"
            "Type *hi* to open the main menu and book."
        ),
        "appointment": (
            "✅ You can book via WhatsApp.\n\n"
            "Type *hi* and choose a service from the menu."
        ),
        "emergency": (
            f"🚑 For emergencies, please call immediately:\n"
            f"📞 {clinic.get('phone', '')}\n"
            f"📞 {clinic.get('alternate_phone', '')}"
        ),
        "about": (
            f"🏥 *About {name}*\n\n"
            f"Type: {clinic.get('type', 'Women & Multi-specialty Hospital')}\n"
            "Helping patients book OPD, ultrasound, lab, pharmacy and IPD support on WhatsApp."
        ),
    }


def get_welcome_message(clinic: dict = None) -> str:
    clinic = clinic or get_clinic_config()
    return f"👋 Welcome to *{clinic.get('name', 'Sudha Hospital')}*.\n\nPlease choose a service."
