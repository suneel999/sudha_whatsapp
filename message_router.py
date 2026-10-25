"""
Message Router - Sudha Hospital payload-based routing
"""

import logging
from typing import Any, Dict, Optional

from button_payloads import (
    GlobalPayload,
    MainMenuPayload,
    GLOBAL_PAYLOADS,
    get_main_menu_payload_from_text,
    is_numeric_input,
    is_valid_payload,
)
from config import get_clinic_config
from handlers.common_booking import about_reply, handle_post_booking, location_reply, main_menu_list
from handlers.ipd_handler import handle_ipd_flow, start_ipd_prompt
from handlers.lab_handler import handle_lab_flow, start_lab_prompt
from handlers.opd_handler import handle_opd_flow, start_opd_prompt
from handlers.pharmacy_handler import handle_pharmacy_flow, start_pharmacy_prompt
from handlers.ultrasound_handler import handle_ultrasound_flow, start_ultrasound_prompt
from state_machine import (
    ConversationState,
    SubState,
    get_session,
    reset_to_main_menu,
    start_ipd_flow,
    start_lab_flow,
    start_opd_flow,
    start_pharmacy_flow,
    start_post_booking,
    start_ultrasound_flow,
    update_session,
)

logger = logging.getLogger(__name__)

TEXT_INPUT_SUBSTATES = {
    SubState.ENTER_NAME.value,
    SubState.ENTER_LMP.value,
    SubState.ENTER_HUSBAND_NAME.value,
    SubState.ENTER_WEEKS.value,
    SubState.ENTER_MEDICINE_NAME.value,
    SubState.WAIT_PRESCRIPTION_IMAGE.value,
}


def route_message(
    user_id: str,
    message: str,
    clinic_id: str = None,
    platform: str = "whatsapp",
    is_button_click: bool = False,
    media: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    message_clean = message.strip() if message else ""
    clinic = get_clinic_config(clinic_id)
    session = get_session(user_id)
    current_state = session.current_state

    logger.info(
        "Routing - User: %s***, State: %s, Message: %s, IsButton: %s",
        user_id[:6],
        current_state,
        message_clean[:50],
        is_button_click,
    )

    if message_clean in GLOBAL_PAYLOADS:
        return _handle_global_payload(user_id, message_clean, clinic)

    if is_button_click:
        return _route_button_click(user_id, message_clean, session, clinic, clinic_id)

    return _route_text_message(user_id, message_clean, session, clinic, clinic_id, media)


def _handle_global_payload(user_id: str, payload: str, clinic: dict) -> Dict[str, Any]:
    if payload == GlobalPayload.MAIN_MENU:
        reset_to_main_menu(user_id)
        return main_menu_list()

    if payload == GlobalPayload.CANCEL:
        reset_to_main_menu(user_id)
        return main_menu_list("Request cancelled.\n\n👋 Welcome to Sudha Hospital.\n\nPlease choose a service.")

    if payload == GlobalPayload.HELP:
        return {
            "text": (
                f"*{clinic['name']} - Help*\n\n"
                "Services:\n"
                "• Out Patient\n"
                "• Ultrasound\n"
                "• Lab Services\n"
                "• Location\n"
                "• About Hospital\n"
                "• Admission\n\n"
                f"📞 Reception: {clinic.get('reception_phone') or clinic.get('phone', '')}\n"
                f"🕒 {clinic.get('hours', '')}\n"
                f"🌐 {clinic.get('website', '')}"
            ),
            "buttons": [{"id": GlobalPayload.MAIN_MENU, "title": "🏠 Main Menu"}],
        }

    reset_to_main_menu(user_id)
    return main_menu_list()


def _route_button_click(user_id: str, payload: str, session, clinic: dict, clinic_id: str):
    current_state = session.current_state

    if not is_valid_payload(payload, current_state):
        logger.warning("Invalid payload %s for state %s", payload, current_state)
        reset_to_main_menu(user_id)
        return main_menu_list("That option isn't available right now. Please choose a service:")

    if current_state == ConversationState.MAIN_MENU.value:
        return _handle_main_menu_payload(user_id, payload, clinic, clinic_id)

    return _dispatch_flow(user_id, payload, session, clinic, clinic_id, is_button=True, media=None)


def _handle_main_menu_payload(user_id: str, payload: str, clinic: dict, clinic_id: str):
    if payload == MainMenuPayload.OPD:
        start_opd_flow(user_id)
        return start_opd_prompt()
    if payload == MainMenuPayload.ULTRASOUND:
        start_ultrasound_flow(user_id)
        return start_ultrasound_prompt()
    if payload == MainMenuPayload.LAB:
        start_lab_flow(user_id)
        return start_lab_prompt()
    if payload == MainMenuPayload.LOCATION:
        reset_to_main_menu(user_id)
        return location_reply(clinic)
    if payload == MainMenuPayload.ABOUT:
        reset_to_main_menu(user_id)
        return about_reply(clinic)
    if payload == MainMenuPayload.PHARMACY:
        # Pharmacy removed — send location / reception instead
        reset_to_main_menu(user_id)
        return location_reply(clinic)
    if payload == MainMenuPayload.IPD:
        start_ipd_flow(user_id)
        return start_ipd_prompt()
    return main_menu_list()


def _route_text_message(
    user_id: str,
    message: str,
    session,
    clinic: dict,
    clinic_id: str,
    media: Optional[Dict[str, Any]] = None,
):
    current_state = session.current_state
    message_lower = message.lower().strip()

    if message_lower in {"hi", "hello", "hey", "start", "menu", "main menu", "home"}:
        reset_to_main_menu(user_id)
        return main_menu_list()

    if message_lower in {"cancel", "stop", "exit", "quit"}:
        reset_to_main_menu(user_id)
        return main_menu_list("Request cancelled.\n\nPlease choose a service.")

    mapped = get_main_menu_payload_from_text(message)
    if mapped and current_state == ConversationState.MAIN_MENU.value:
        if mapped in GLOBAL_PAYLOADS:
            return _handle_global_payload(user_id, mapped, clinic)
        return _handle_main_menu_payload(user_id, mapped, clinic, clinic_id)

    if current_state != ConversationState.MAIN_MENU.value:
        # Allow image/media in pharmacy upload state even if text empty-ish
        if current_state == ConversationState.PHARMACY_FLOW.value and media:
            return _dispatch_flow(user_id, message or "__MEDIA__", session, clinic, clinic_id, False, media)

        if session.sub_state in TEXT_INPUT_SUBSTATES or session.sub_state in {
            SubState.SELECT_DATE.value,
            SubState.SELECT_TIME.value,
            SubState.CONFIRM.value,
            SubState.SELECT_SYMPTOMS.value,
            SubState.POST_CONFIRM.value,
            SubState.CONFIRM_CANCEL.value,
        }:
            return _dispatch_flow(user_id, message, session, clinic, clinic_id, False, media)

    if is_numeric_input(message) and current_state == ConversationState.MAIN_MENU.value:
        mapped = get_main_menu_payload_from_text(message)
        if mapped:
            return _handle_main_menu_payload(user_id, mapped, clinic, clinic_id)

    if current_state == ConversationState.MAIN_MENU.value:
        return main_menu_list("I'm here to help! Please choose a service:")

    return main_menu_list("Please use the buttons below to continue:")


def _dispatch_flow(
    user_id: str,
    message: str,
    session,
    clinic: dict,
    clinic_id: str,
    is_button: bool,
    media: Optional[Dict[str, Any]],
):
    state = session.current_state
    booking_ctx = None

    if state == ConversationState.OPD_FLOW.value:
        response, complete, booking_ctx = handle_opd_flow(session, message, clinic, clinic_id, is_button)
    elif state == ConversationState.ULTRASOUND_FLOW.value:
        response, complete, booking_ctx = handle_ultrasound_flow(session, message, clinic, clinic_id, is_button)
    elif state == ConversationState.LAB_FLOW.value:
        response, complete, booking_ctx = handle_lab_flow(session, message, clinic, clinic_id, is_button)
    elif state == ConversationState.PHARMACY_FLOW.value:
        response, complete, booking_ctx = handle_pharmacy_flow(
            session, message, clinic, clinic_id, is_button, media=media
        )
    elif state == ConversationState.IPD_FLOW.value:
        response, complete, booking_ctx = handle_ipd_flow(session, message, clinic, clinic_id, is_button)
    elif state == ConversationState.POST_BOOKING.value:
        response, complete = handle_post_booking(session, message, clinic, is_button)
        booking_ctx = None
    else:
        reset_to_main_menu(user_id)
        return main_menu_list()

    if complete and booking_ctx:
        start_post_booking(user_id, booking_ctx)
        update_session(get_session(user_id))
        return response

    if complete:
        reset_to_main_menu(user_id)
    else:
        update_session(session)

    return response
