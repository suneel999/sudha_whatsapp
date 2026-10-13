"""
Intent Router
Decides message handling BEFORE any AI call.
AI is ONLY called as a last resort fallback.

ARCHITECTURE (STATE MACHINE):
1. Check conversation state FIRST
2. If APPOINTMENT_FLOW mode -> ignore normal messages (Flow handles via /flow webhook)
3. If DIAGNOSTICS or ADMISSION mode -> route to those handlers, NEVER check main menu
4. If MENU mode -> then check main menu numbers (1, 2, 3)

CRITICAL: Menu numbers are scoped to current mode - prevents collision!
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
from enum import Enum

from session_manager import has_active_session, get_session, get_session_type
from conversation_state import (
    get_user_state, is_flow_active, is_in_menu, is_in_diagnostics, is_in_admission,
    start_appointment_flow_mode, start_diagnostics_mode, start_admission_mode,
    complete_flow_and_reset, should_ignore_message
)
from faq_handler import match_faq
from booking_engine import (
    start_appointment_flow, process_booking_input,
    start_diagnostics_flow, process_diagnostics_input,
    start_admission_flow, process_admission_input,
    cancel_booking, check_status
)
from ai_fallback import get_ai_response, is_allowed_for_ai, FALLBACK_MESSAGE
from data_safety import contains_medical_query
from config import get_main_menu_keywords, get_clinic_config

logger = logging.getLogger(__name__)

# Flow configuration - set FLOW_ID to enable WhatsApp Flows for appointment booking
FLOW_ID = os.getenv('FLOW_ID', '')
USE_FLOWS = bool(FLOW_ID)


class IntentType(Enum):
    """Explicit intent types for routing decisions."""
    
    # Priority 0: Flow states
    FLOW_COMPLETED = "flow_completed"
    FLOW_ACTIVE_IGNORE = "flow_active_ignore"  # Flow is active - ignore normal messages
    
    # Priority 1: Active session handling (text-based flows)
    APPOINTMENT_IN_PROGRESS = "appointment_in_progress"
    DIAGNOSTICS_IN_PROGRESS = "diagnostics_in_progress"
    ADMISSION_IN_PROGRESS = "admission_in_progress"
    
    # Priority 2: Fixed commands - Main Menu Options (ONLY when in MENU mode)
    GREETING = "greeting"  # Show main menu
    START_APPOINTMENT = "start_appointment"
    START_APPOINTMENT_FLOW = "start_appointment_flow"  # Use Flow
    START_DIAGNOSTICS = "start_diagnostics"
    START_ADMISSION = "start_admission"
    CANCEL_BOOKING = "cancel_booking"
    CHECK_STATUS = "check_status"
    HELP = "help"
    
    # Priority 3: FAQ match
    FAQ_MATCH = "faq_match"
    
    # Priority 4: Blocked queries
    MEDICAL_QUERY = "medical_query"
    
    # Priority 5: AI fallback (last resort)
    AI_FALLBACK = "ai_fallback"
    
    # Catch-all
    UNKNOWN = "unknown"


# Command keyword mappings
GREETING_KEYWORDS = frozenset(['hi', 'hello', 'hey', 'start', 'menu', 'main menu', 'home'])
HELP_KEYWORDS = frozenset(['help', 'options', 'what can you do', 'commands'])
CANCEL_KEYWORDS = frozenset(['cancel'])
STATUS_KEYWORDS = frozenset(['status', 'check', 'my appointment', 'booking status', 'my booking'])


def detect_intent(user_id: str, message: str) -> Tuple[IntentType, Dict[str, Any]]:
    """
    Detect user intent from message using STATE MACHINE.
    
    CRITICAL ARCHITECTURE:
    1. Check conversation state FIRST
    2. If APPOINTMENT_FLOW mode -> ignore (Flow handles via /flow webhook)
    3. If DIAGNOSTICS/ADMISSION mode -> route to those handlers, numbers are SCOPED
    4. If MENU mode -> then check main menu numbers (1, 2, 3)
    
    Returns:
        Tuple of (IntentType, context_dict)
    """
    message_clean = message.strip()
    message_lower = message_clean.lower()
    context: Dict[str, Any] = {'original_message': message_clean}
    
    # Get current conversation state
    user_state = get_user_state(user_id)
    current_mode = user_state.get("mode", "MENU")
    context['current_mode'] = current_mode
    
    logger.info(f"Detecting intent - Mode: {current_mode}, Message: {message_clean[:50]}")
    
    # ============================================
    # PRIORITY 0: Check for Flow completion marker
    # ============================================
    if message_clean == '__FLOW_COMPLETED__':
        logger.info("Intent: FLOW_COMPLETED")
        return IntentType.FLOW_COMPLETED, context
    
    # ============================================
    # PRIORITY 0.5: If Flow is ACTIVE, ignore normal messages
    # ============================================
    if current_mode == "APPOINTMENT_FLOW":
        # CRITICAL: During active Flow, we must ignore all normal messages
        # The user is interacting with the Flow UI, not the chat
        # Allow only explicit cancel/menu commands to break out
        if message_lower in ['cancel', 'stop', 'menu', 'exit']:
            logger.info("Flow mode: User requested exit")
            complete_flow_and_reset(user_id)
            return IntentType.GREETING, context
        
        logger.info("Intent: FLOW_ACTIVE_IGNORE - Flow is active, ignoring chat message")
        return IntentType.FLOW_ACTIVE_IGNORE, context
    
    # ============================================
    # PRIORITY 1: DIAGNOSTICS MODE - scoped number handling
    # ============================================
    if current_mode == "DIAGNOSTICS":
        # In diagnostics mode, ALL input goes to diagnostics handler
        # Numbers 1-7 are for test selection, NOT main menu
        session = get_session(user_id)
        if session:
            context['session'] = session
            context['current_step'] = session.step
            logger.info(f"Intent: DIAGNOSTICS_IN_PROGRESS (step: {session.step})")
            return IntentType.DIAGNOSTICS_IN_PROGRESS, context
        else:
            # Session expired or missing, reset to menu
            complete_flow_and_reset(user_id)
    
    # ============================================
    # PRIORITY 1: ADMISSION MODE - scoped number handling
    # ============================================
    if current_mode == "ADMISSION":
        # In admission mode, ALL input goes to admission handler
        # Numbers 1-3 are for type/gender selection, NOT main menu
        session = get_session(user_id)
        if session:
            context['session'] = session
            context['current_step'] = session.step
            logger.info(f"Intent: ADMISSION_IN_PROGRESS (step: {session.step})")
            return IntentType.ADMISSION_IN_PROGRESS, context
        else:
            # Session expired or missing, reset to menu
            complete_flow_and_reset(user_id)
    
    # ============================================
    # PRIORITY 1: Check for legacy appointment sessions (text-based fallback)
    # ============================================
    if has_active_session(user_id):
        session = get_session(user_id)
        if session:
            session_type = get_session_type(user_id)
            context['session'] = session
            context['current_step'] = session.step
            
            if session_type == 'diagnostics':
                logger.info(f"Intent: DIAGNOSTICS_IN_PROGRESS (step: {session.step})")
                return IntentType.DIAGNOSTICS_IN_PROGRESS, context
            elif session_type == 'admission':
                logger.info(f"Intent: ADMISSION_IN_PROGRESS (step: {session.step})")
                return IntentType.ADMISSION_IN_PROGRESS, context
            else:
                # Text-based appointment flow (when Flows disabled)
                logger.info(f"Intent: APPOINTMENT_IN_PROGRESS (step: {session.step})")
                return IntentType.APPOINTMENT_IN_PROGRESS, context
    
    # ============================================
    # MENU MODE: Main Menu Selection (1, 2, 3)
    # Numbers are ONLY interpreted as menu options here
    # ============================================
    menu_keywords = get_main_menu_keywords()
    
    # Check for appointment keywords/number "1"
    if message_lower in menu_keywords["appointment"] or any(
        kw in message_lower for kw in menu_keywords["appointment"] if len(kw) > 2
    ):
        # Check if Flow is already active to prevent re-triggering
        if is_flow_active(user_id):
            logger.warning("Attempted to start appointment while Flow already active")
            return IntentType.FLOW_ACTIVE_IGNORE, context
        
        if USE_FLOWS:
            logger.info("Intent: START_APPOINTMENT_FLOW")
            return IntentType.START_APPOINTMENT_FLOW, context
        else:
            logger.info("Intent: START_APPOINTMENT")
            return IntentType.START_APPOINTMENT, context
    
    # Check for diagnostics keywords/number "2"
    if message_lower in menu_keywords["diagnostics"] or any(
        kw in message_lower for kw in menu_keywords["diagnostics"] if len(kw) > 2
    ):
        logger.info("Intent: START_DIAGNOSTICS")
        return IntentType.START_DIAGNOSTICS, context
    
    # Check for admission keywords/number "3"
    if message_lower in menu_keywords["admission"] or any(
        kw in message_lower for kw in menu_keywords["admission"] if len(kw) > 2
    ):
        logger.info("Intent: START_ADMISSION")
        return IntentType.START_ADMISSION, context
    
    # ============================================
    # PRIORITY 3: Fixed commands (always available)
    # ============================================
    
    # Greetings - Show main menu
    if message_lower in GREETING_KEYWORDS or any(
        message_lower.startswith(kw + ' ') for kw in GREETING_KEYWORDS
    ):
        logger.info("Intent: GREETING")
        return IntentType.GREETING, context
    
    # Help command
    if message_lower in HELP_KEYWORDS:
        logger.info("Intent: HELP")
        return IntentType.HELP, context
    
    # Cancel booking (extract booking ID if present)
    if any(kw in message_lower for kw in CANCEL_KEYWORDS):
        words = message_clean.split()
        booking_id = None
        for word in words:
            word_upper = word.upper()
            if word_upper.startswith('APT') or word_upper.startswith('DGN') or word_upper.startswith('ADM'):
                if len(word_upper) >= 8:
                    booking_id = word_upper
                    break
        context['booking_id'] = booking_id
        logger.info(f"Intent: CANCEL_BOOKING (id: {booking_id})")
        return IntentType.CANCEL_BOOKING, context
    
    # Check status (extract booking ID if present)
    if any(kw in message_lower for kw in STATUS_KEYWORDS):
        words = message_clean.split()
        booking_id = None
        for word in words:
            word_upper = word.upper()
            if word_upper.startswith('APT') or word_upper.startswith('DGN') or word_upper.startswith('ADM'):
                if len(word_upper) >= 8:
                    booking_id = word_upper
                    break
        context['booking_id'] = booking_id
        logger.info(f"Intent: CHECK_STATUS (id: {booking_id})")
        return IntentType.CHECK_STATUS, context
    
    # ============================================
    # PRIORITY 4: FAQ keyword match
    # ============================================
    faq_result = match_faq(message)
    if faq_result:
        context['faq_key'] = faq_result[0]
        context['faq_response'] = faq_result[1]
        logger.info(f"Intent: FAQ_MATCH ({faq_result[0]})")
        return IntentType.FAQ_MATCH, context
    
    # ============================================
    # PRIORITY 5: Medical query (blocked)
    # ============================================
    if contains_medical_query(message):
        logger.info("Intent: MEDICAL_QUERY (blocked)")
        return IntentType.MEDICAL_QUERY, context
    
    # ============================================
    # PRIORITY 6: AI fallback (only if allowed)
    # ============================================
    if is_allowed_for_ai(message):
        logger.info("Intent: AI_FALLBACK")
        return IntentType.AI_FALLBACK, context
    
    # ============================================
    # FALLBACK: Show main menu (treat as greeting)
    # ============================================
    logger.info("Intent: GREETING (fallback - showing main menu)")
    return IntentType.GREETING, context


def route_message(user_id: str, message: str, clinic_id: str = None, platform: str = 'whatsapp') -> Optional[Any]:
    """
    Route message to appropriate handler based on detected intent.
    
    STATE MACHINE ROUTING:
    - APPOINTMENT_FLOW mode: Ignore normal messages (return None)
    - DIAGNOSTICS/ADMISSION mode: Route to text flow handlers
    - MENU mode: Process main menu options
    
    AI is ONLY called for AI_FALLBACK intent.
    
    Args:
        user_id: User's phone number / identifier
        message: User's message text
        clinic_id: Optional clinic identifier for multi-clinic support
        platform: 'whatsapp', 'instagram', or 'facebook'
    
    Returns:
        Response content: string (text) or dict (text + buttons), 
        or None if Flow is sent or message should be ignored
    """
    intent, context = detect_intent(user_id, message)
    clinic = get_clinic_config(clinic_id)
    
    # ============================================
    # Handle each intent type
    # ============================================
    
    if intent == IntentType.FLOW_ACTIVE_IGNORE:
        # CRITICAL: Flow is active - ignore this chat message
        # User is interacting with Flow UI, not chat
        logger.info(f"Ignoring chat message - Flow active for {user_id[:6]}***")
        return None
    
    if intent == IntentType.FLOW_COMPLETED:
        # Flow was completed - appointment already saved by flow_handler
        # Reset state to MENU
        complete_flow_and_reset(user_id)
        return _get_flow_completed_message(clinic)
    
    if intent == IntentType.APPOINTMENT_IN_PROGRESS:
        # Continue text-based appointment flow (only if Flows disabled)
        response, complete = process_booking_input(user_id, message, clinic_id)
        if complete:
            complete_flow_and_reset(user_id)
        _handle_booking_complete(complete, response, user_id, platform)
        return response
    
    if intent == IntentType.DIAGNOSTICS_IN_PROGRESS:
        # Continue diagnostics flow - numbers are SCOPED here
        response, complete = process_diagnostics_input(user_id, message, clinic_id)
        if complete:
            complete_flow_and_reset(user_id)
        _handle_booking_complete(complete, response, user_id, platform)
        return response
    
    if intent == IntentType.ADMISSION_IN_PROGRESS:
        # Continue admission flow - numbers are SCOPED here
        response, complete = process_admission_input(user_id, message, clinic_id)
        if complete:
            complete_flow_and_reset(user_id)
        _handle_booking_complete(complete, response, user_id, platform)
        return response
    
    elif intent == IntentType.GREETING:
        # Return welcome message with main menu
        # Ensure we're in MENU mode
        complete_flow_and_reset(user_id)
        return _get_welcome_message(clinic)
    
    elif intent == IntentType.HELP:
        # Return help message
        return _get_help_message()
    
    elif intent == IntentType.START_APPOINTMENT_FLOW:
        # CRITICAL: Check if Flow already active to prevent white screen
        if is_flow_active(user_id):
            logger.warning("Attempted to send Flow while one is already active")
            return None  # Don't send another Flow
        
        # Set state BEFORE sending Flow
        from datetime import datetime
        flow_token = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        start_appointment_flow_mode(user_id, flow_token)
        
        # Send WhatsApp Flow for appointment booking
        from flow_handler import send_flow_message
        success = send_flow_message(user_id, FLOW_ID, clinic_id, flow_token)
        
        if success:
            logger.info(f"Flow sent successfully, mode set to APPOINTMENT_FLOW")
            return None  # Flow message sent, no text response needed
        else:
            # Fallback to text-based booking if Flow fails
            logger.warning("Flow send failed, falling back to text booking")
            complete_flow_and_reset(user_id)  # Reset state
            response, _ = start_appointment_flow(user_id, clinic_id)
            return response
    
    elif intent == IntentType.START_APPOINTMENT:
        # Start text-based appointment flow
        response, _ = start_appointment_flow(user_id, clinic_id)
        return response
    
    elif intent == IntentType.START_DIAGNOSTICS:
        # Set DIAGNOSTICS mode FIRST
        start_diagnostics_mode(user_id, "SELECT_TEST")
        # Start diagnostics flow
        response, _ = start_diagnostics_flow(user_id, clinic_id)
        return response
    
    elif intent == IntentType.START_ADMISSION:
        # Set ADMISSION mode FIRST
        start_admission_mode(user_id, "TYPE")
        # Start admission flow
        response, _ = start_admission_flow(user_id, clinic_id)
        return response
    
    elif intent == IntentType.CANCEL_BOOKING:
        # Cancel booking
        return cancel_booking(user_id, context.get('booking_id'))
    
    elif intent == IntentType.CHECK_STATUS:
        # Check booking status
        return check_status(user_id, context.get('booking_id'))
    
    elif intent == IntentType.FAQ_MATCH:
        # Return FAQ response
        return context['faq_response']
    
    elif intent == IntentType.MEDICAL_QUERY:
        # Blocked - return safe message
        return _get_medical_query_response()
    
    elif intent == IntentType.AI_FALLBACK:
        # ONLY place where AI is called
        from crm_handler import get_crm_context
        crm_context = get_crm_context(user_id, platform)
        return get_ai_response(message, clinic_id, user_id, crm_context=crm_context)
    
    else:  # IntentType.UNKNOWN
        # Return welcome message (main menu)
        return _get_welcome_message(clinic)


def _handle_booking_complete(complete: bool, response: str, user_id: str, platform: str):
    """Handle post-booking CRM updates."""
    if complete and "Confirmed" in str(response):
        from crm_handler import handle_booking_confirmed, update_patient_name
        handle_booking_confirmed(user_id, platform)
        
        session = get_session(user_id)
        if session and session.get_value('patient_name'):
            update_patient_name(user_id, platform, session.get_value('patient_name'))


def _get_welcome_message(clinic: dict) -> str:
    """Return welcome message with main menu options."""
    return f"""Thank you for visiting *{clinic['name']}* 🙏

Please choose a service:

1️⃣ Appointment
2️⃣ Diagnostics
3️⃣ Admission

Reply with *number* or *text*.

_For emergencies, call: {clinic['phone']}_"""


def _get_flow_completed_message(clinic: dict) -> str:
    """
    Return message after flow completion.
    NOTE: The detailed confirmation is sent by flow_handler via app.py
    This is a fallback message if Flow completes without proper confirmation.
    """
    return f"""Thank you for choosing *{clinic['name']}*!

Your appointment request has been processed.

_Please arrive 15 minutes before your appointment._

Type *menu* to return to main menu."""


def _get_help_message() -> str:
    """Return help message with available commands."""
    return """*Mallika Hospitals - Help Menu*

━━━━━━━━━━━━━━━━━━━━━
*MAIN SERVICES*
━━━━━━━━━━━━━━━━━━━━━
*1* - Book Appointment
*2* - Diagnostics
*3* - Admission

━━━━━━━━━━━━━━━━━━━━━
*OTHER COMMANDS*
━━━━━━━━━━━━━━━━━━━━━
*cancel [ID]* - Cancel booking
*status [ID]* - Check booking status
*menu* - Main menu

━━━━━━━━━━━━━━━━━━━━━
*INFORMATION*
━━━━━━━━━━━━━━━━━━━━━
*contact* - Phone & email
*hours* - OPD & emergency timings  
*address* - Hospital location
*doctors* - Our medical team
*emergency* - 24x7 urgent care

━━━━━━━━━━━━━━━━━━━━━
*Reception:* +91 98854 54128"""


def _get_medical_query_response() -> str:
    """Return safe response for medical queries."""
    return """*Medical Advice Notice*

I'm unable to provide medical advice, diagnoses, or treatment recommendations.

For health concerns, please:
*1* - Book an appointment with our specialists
*2* - Call emergency for urgent care: +91 98854 54128

_Your health is important - consult our qualified doctors._

Type *1* to book an appointment or *menu* for main menu."""
