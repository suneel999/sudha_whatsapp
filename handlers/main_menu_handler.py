"""Main menu helpers for Sudha Hospital."""

from typing import Any, Dict, Optional

from handlers.common_booking import main_menu_list
from button_payloads import GlobalPayload


def get_main_menu_buttons(clinic: dict, intro_text: str = None) -> Dict[str, Any]:
    return main_menu_list(intro_text)


def get_help_message(clinic: dict) -> Dict[str, Any]:
    body = f"""*{clinic['name']} - Help*

Services:
• Out Patient Services
• Ultrasound Scanning
• Lab Services
• Pharmacy
• In Patient Services

📞 Reception: {clinic.get('phone', '')}
🕒 {clinic.get('hours', '')}
🌐 {clinic.get('website', '')}"""
    return {
        "text": body,
        "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
    }


def check_faq(message: str) -> Optional[str]:
    try:
        from faq_handler import match_faq

        faq_result = match_faq(message)
        if faq_result:
            return faq_result[1]
    except Exception:
        return None
    return None
