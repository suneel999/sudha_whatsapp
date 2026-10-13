"""
Conversation State Machine
Manages user conversation modes to prevent state mixing between:
- MENU: Main menu text selection
- APPOINTMENT_FLOW: Meta WhatsApp Flow (active until Flow completes)
- DIAGNOSTICS: Text-based diagnostics booking
- ADMISSION: Text-based admission request

CRITICAL RULES:
1. MENU handles free text / numbers for main menu only
2. APPOINTMENT_FLOW is Meta Flow ONLY - ignore all normal messages
3. DIAGNOSTICS and ADMISSION are text-driven sub-flows
4. NEVER mix them - each mode is isolated
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any

from database import (
    get_conversation_state,
    set_conversation_state,
    update_conversation_context,
    reset_conversation_state,
    delete_conversation_state
)

logger = logging.getLogger(__name__)


class ConversationMode(Enum):
    """User conversation modes - mutually exclusive."""
    # UPDATED: Using consistent state names with state_machine.py
    MENU = "MAIN_MENU"                     # Main menu - handles 1/2/3 selection
    APPOINTMENT_FLOW = "APPOINTMENT_FLOW"  # Meta Flow active - ignore chat
    DIAGNOSTICS = "DIAGNOSTICS_FLOW"       # Text-based diagnostics
    ADMISSION = "ADMISSION_FLOW"           # Text-based admission


# State timeout in seconds (30 minutes for Flow, handled differently)
STATE_TIMEOUT = 1800


def get_user_state(user_id: str) -> Dict[str, Any]:
    """
    Get current conversation state for user.
    Returns default MAIN_MENU state if none exists.
    """
    state = get_conversation_state(user_id)
    
    if state:
        # Map old state names to new ones for backwards compatibility
        stored_mode = state.get("mode", "MAIN_MENU")
        mode_mapping = {
            "MENU": "MAIN_MENU",
            "DIAGNOSTICS": "DIAGNOSTICS_FLOW",
            "ADMISSION": "ADMISSION_FLOW",
        }
        mapped_mode = mode_mapping.get(stored_mode, stored_mode)
        
        return {
            "mode": mapped_mode,
            "sub_step": state.get("sub_step"),
            "context": state.get("context", {}),
            "flow_token": state.get("flow_token")
        }
    
    # Default state
    return {
        "mode": "MAIN_MENU",
        "sub_step": None,
        "context": {},
        "flow_token": None
    }


def is_flow_active(user_id: str) -> bool:
    """Check if user has an active Meta Flow session."""
    state = get_user_state(user_id)
    return state["mode"] == ConversationMode.APPOINTMENT_FLOW.value


def is_in_menu(user_id: str) -> bool:
    """Check if user is in main menu state."""
    state = get_user_state(user_id)
    return state["mode"] == ConversationMode.MENU.value


def is_in_diagnostics(user_id: str) -> bool:
    """Check if user is in diagnostics flow."""
    state = get_user_state(user_id)
    return state["mode"] == ConversationMode.DIAGNOSTICS.value


def is_in_admission(user_id: str) -> bool:
    """Check if user is in admission flow."""
    state = get_user_state(user_id)
    return state["mode"] == ConversationMode.ADMISSION.value


def start_appointment_flow_mode(user_id: str, flow_token: str = None):
    """
    Set user to APPOINTMENT_FLOW mode.
    Call this BEFORE sending the Flow message.
    """
    logger.info(f"Starting APPOINTMENT_FLOW mode for {user_id[:6]}***")
    set_conversation_state(
        user_id=user_id,
        mode=ConversationMode.APPOINTMENT_FLOW.value,
        sub_step="FLOW_ACTIVE",
        context={},
        flow_token=flow_token
    )


def start_diagnostics_mode(user_id: str, sub_step: str = "SELECT_TEST"):
    """Set user to DIAGNOSTICS_FLOW mode."""
    logger.info(f"Starting DIAGNOSTICS_FLOW mode for {user_id[:6]}***")
    set_conversation_state(
        user_id=user_id,
        mode=ConversationMode.DIAGNOSTICS.value,
        sub_step=sub_step,
        context={}
    )


def start_admission_mode(user_id: str, sub_step: str = "TYPE"):
    """Set user to ADMISSION_FLOW mode."""
    logger.info(f"Starting ADMISSION_FLOW mode for {user_id[:6]}***")
    set_conversation_state(
        user_id=user_id,
        mode=ConversationMode.ADMISSION.value,
        sub_step=sub_step,
        context={}
    )


def update_state_context(user_id: str, **kwargs):
    """Update context data without changing mode."""
    update_conversation_context(user_id, kwargs)


def update_sub_step(user_id: str, sub_step: str):
    """Update the sub_step for current mode."""
    state = get_user_state(user_id)
    set_conversation_state(
        user_id=user_id,
        mode=state["mode"],
        sub_step=sub_step,
        context=state["context"],
        flow_token=state.get("flow_token")
    )


def complete_flow_and_reset(user_id: str):
    """
    Complete the current flow and reset to MENU.
    Call this after Flow completes or booking is confirmed.
    """
    logger.info(f"Completing flow and resetting to MENU for {user_id[:6]}***")
    reset_conversation_state(user_id)


def reset_to_menu(user_id: str):
    """Alias for complete_flow_and_reset."""
    complete_flow_and_reset(user_id)


def should_ignore_message(user_id: str) -> bool:
    """
    Check if normal messages should be ignored.
    Returns True if user is in APPOINTMENT_FLOW mode.
    
    CRITICAL: During Meta Flow, we must ignore all normal chat messages.
    Only the /flow webhook should process Flow data.
    """
    return is_flow_active(user_id)


def get_mode_display_name(mode: str) -> str:
    """Get human-readable mode name."""
    names = {
        # New state names
        "MAIN_MENU": "Main Menu",
        "DIAGNOSTICS_FLOW": "Diagnostics Booking",
        "ADMISSION_FLOW": "Admission Request",
        "APPOINTMENT_FLOW": "Appointment Booking (Flow)",
        "TEXT_APPOINTMENT": "Appointment Booking (Text)",
        # Old state names (backwards compatibility)
        "MENU": "Main Menu",
        "DIAGNOSTICS": "Diagnostics Booking",
        "ADMISSION": "Admission Request"
    }
    return names.get(mode, mode)
