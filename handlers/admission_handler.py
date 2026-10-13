"""
Admission Flow Handler - Button-Based Hospital Admission

=============================================================================
ENTERPRISE-GRADE BUTTON ROUTING
=============================================================================

This handler processes hospital admission requests using buttons.

FLOW:
1. SELECT_TYPE: User clicks admission type button (EMERGENCY/NON_EMERGENCY)
2. For EMERGENCY: Show emergency contact info immediately
3. For NON_EMERGENCY:
   - ENTER_NAME: User types patient name (or clicks WALKIN)
   - ENTER_AGE: User types age
   - SELECT_GENDER: User clicks gender button
   - SELECT_DATE: User clicks preferred admission date button
   - CONFIRM: User clicks confirm/cancel button

CRITICAL:
- Admission type selection is ONLY via button payload
- Gender selection is ONLY via button payload  
- Date selection is ONLY via button payload
- Text input only for name and age
- Emergency immediately shows call info + ICU message

=============================================================================
"""

import logging
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta

from state_machine import Session, SubState
from button_payloads import (
    AdmissionPayload, GlobalPayload, MainMenuPayload,
    GENDER_PAYLOAD_MAP
)
from database import save_admission

logger = logging.getLogger(__name__)

# Date payload prefix for admission
ADMISSION_DATE_PREFIX = "ADMISSION_DATE_"


def handle_admission_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False
) -> Tuple[Dict[str, Any], bool]:
    """
    Handle hospital admission flow.
    
    Args:
        session: User's session object
        message: Button payload ID or text input
        clinic: Clinic configuration
        clinic_id: Clinic ID
        is_button: True if message is a button payload
    
    Returns:
        Tuple of (response_dict, is_complete)
        is_complete=True means flow is done, reset to main menu
    """
    sub_state = session.sub_state
    
    logger.info(f"Admission handler - SubState: {sub_state}, "
                f"Message: {message[:30]}, IsButton: {is_button}")
    
    # Handle global navigation payloads
    if message == AdmissionPayload.BACK_TO_MENU or message == GlobalPayload.MAIN_MENU:
        return _get_cancelled_response(), True
    
    if message == GlobalPayload.CANCEL:
        return _get_cancelled_response(), True
    
    # Route to appropriate sub-state handler
    if sub_state == SubState.SELECT_TYPE.value:
        return _handle_type_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.ENTER_NAME.value:
        return _handle_name_input(session, message, clinic, is_button)
    
    elif sub_state == SubState.ENTER_AGE.value:
        return _handle_age_input(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_GENDER.value:
        return _handle_gender_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_DATE.value:
        return _handle_date_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.CONFIRM.value:
        return _handle_confirmation(session, message, clinic, clinic_id, is_button)
    
    # Unknown sub-state - show type selection
    session.set_sub_state(SubState.SELECT_TYPE)
    return _get_admission_menu_response(), False


def _handle_type_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """
    Handle admission type selection via button.
    
    CRITICAL: Only accepts button payloads.
    """
    
    # Only accept button clicks
    if not is_button:
        return _get_admission_menu_response(
            "Please tap a button below to select admission type:"
        ), False
    
    # EMERGENCY ADMISSION
    if message == AdmissionPayload.EMERGENCY:
        logger.info("Admission: EMERGENCY selected")
        session.set_context('admission_type', 'Emergency')
        
        # For emergency, show contact info immediately
        return _get_emergency_response(clinic), True
    
    # NON-EMERGENCY (PLANNED) ADMISSION
    if message == AdmissionPayload.NON_EMERGENCY:
        logger.info("Admission: NON_EMERGENCY selected")
        session.set_context('admission_type', 'Non-Emergency')
        session.set_sub_state(SubState.ENTER_NAME)
        
        return {
            'text': """*Planned Admission* 🏥

━━━━━━━━━━━━━━━━━━━━━

*Enter Patient Name:*
Please type the full name of the patient.

Or tap the button below if patient will provide details at reception:""",
            'buttons': [
                {'id': AdmissionPayload.WALKIN, 'title': '🚶 Walk-in Patient'}
            ]
        }, False
    
    # Invalid - show menu again
    return _get_admission_menu_response(), False


def _handle_name_input(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle patient name input (text or walk-in button)."""
    
    # Handle walk-in button
    if is_button and message == AdmissionPayload.WALKIN:
        session.set_context('patient_name', 'Walk-in Patient')
        session.set_context('is_walkin', True)
        session.set_sub_state(SubState.CONFIRM)
        
        ctx = session.context
        
        return {
            'text': f"""*Confirm Walk-in Admission Request*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
🏥 Type: {ctx.get('admission_type', 'N/A')}
👤 Patient: Walk-in (Details at reception)
━━━━━━━━━━━━━━━━━━━━━

Please confirm:""",
            'buttons': [
                {'id': AdmissionPayload.CONFIRM_YES, 'title': '✅ Confirm Request'},
                {'id': AdmissionPayload.CONFIRM_NO, 'title': '❌ Cancel'}
            ]
        }, False
    
    # Text input for name
    if is_button:
        return {
            'text': "Please *type* the patient's name:",
            'buttons': [
                {'id': AdmissionPayload.WALKIN, 'title': '🚶 Walk-in Patient'}
            ]
        }, False
    
    name = message.strip()
    
    # Validate name
    if len(name) < 2:
        return {
            'text': "❌ Name too short.\n\nPlease enter a valid name (at least 2 characters):",
            'buttons': [
                {'id': AdmissionPayload.WALKIN, 'title': '🚶 Walk-in Patient'}
            ]
        }, False
    
    if len(name) > 100:
        return {
            'text': "❌ Name too long.\n\nPlease enter a shorter name:"
        }, False
    
    if any(char.isdigit() for char in name):
        return {
            'text': "❌ Name should not contain numbers.\n\nPlease enter a valid name:"
        }, False
    
    # Save name and move to age input
    session.set_context('patient_name', name)
    session.set_context('is_walkin', False)
    session.set_sub_state(SubState.ENTER_AGE)
    
    return {
        'text': f"""✅ Patient: *{name}*

━━━━━━━━━━━━━━━━━━━━━

*Enter Patient Age:*
Please type the patient's age in years:"""
    }, False


def _handle_age_input(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle age input (text only)."""
    
    if is_button:
        return {
            'text': "Please *type* the patient's age in years:"
        }, False
    
    try:
        age = int(message.strip())
        
        if age < 0 or age > 150:
            return {
                'text': "❌ Please enter a valid age (0-150):"
            }, False
        
        # Save age and move to gender selection
        session.set_context('age', str(age))
        session.set_sub_state(SubState.SELECT_GENDER)
        
        return {
            'text': f"""✅ Age: *{age} years*

━━━━━━━━━━━━━━━━━━━━━

*Select Patient Gender:*""",
            'buttons': [
                {'id': AdmissionPayload.GENDER_MALE, 'title': '👨 Male'},
                {'id': AdmissionPayload.GENDER_FEMALE, 'title': '👩 Female'},
                {'id': AdmissionPayload.GENDER_OTHER, 'title': '⚧ Other'}
            ]
        }, False
    
    except ValueError:
        return {
            'text': "❌ Please enter a valid age number:"
        }, False


def _handle_gender_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle gender selection via button."""
    
    # Only accept button clicks for gender
    if not is_button:
        return {
            'text': "Please tap a button to select gender:",
            'buttons': [
                {'id': AdmissionPayload.GENDER_MALE, 'title': '👨 Male'},
                {'id': AdmissionPayload.GENDER_FEMALE, 'title': '👩 Female'},
                {'id': AdmissionPayload.GENDER_OTHER, 'title': '⚧ Other'}
            ]
        }, False
    
    # Check valid gender payload
    if message in GENDER_PAYLOAD_MAP:
        gender = GENDER_PAYLOAD_MAP[message]
        session.set_context('sex', gender)
        session.set_sub_state(SubState.SELECT_DATE)
        
        return _get_date_selection_response(gender), False
    
    # Invalid - show gender buttons again
    return {
        'text': "Please select a gender:",
        'buttons': [
            {'id': AdmissionPayload.GENDER_MALE, 'title': '👨 Male'},
            {'id': AdmissionPayload.GENDER_FEMALE, 'title': '👩 Female'},
            {'id': AdmissionPayload.GENDER_OTHER, 'title': '⚧ Other'}
        ]
    }, False


def _handle_date_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle admission date selection via button."""
    
    # Only accept button clicks for date selection
    if not is_button:
        gender = session.get_context('sex', '')
        return _get_date_selection_response(gender,
            "Please tap a button to select your preferred admission date:"), False
    
    # Check if it's a date payload
    if message.startswith(ADMISSION_DATE_PREFIX):
        date_str = message.replace(ADMISSION_DATE_PREFIX, '')
        
        session.set_context('preferred_date', date_str)
        session.set_sub_state(SubState.CONFIRM)
        
        logger.info(f"Admission: Date selected - {date_str}")
        
        # Show confirmation
        ctx = session.context
        
        return {
            'text': f"""*Confirm Admission Request*

━━━━━━━━━━━━━━━━━━━━━
*Patient Details:*
━━━━━━━━━━━━━━━━━━━━━
🏥 Type: {ctx.get('admission_type', 'N/A')}
👤 Name: {ctx.get('patient_name', 'N/A')}
🎂 Age: {ctx.get('age', 'N/A')} years
⚧ Gender: {ctx.get('sex', 'N/A')}
📅 Preferred Date: {date_str}
━━━━━━━━━━━━━━━━━━━━━

Please confirm:""",
            'buttons': [
                {'id': AdmissionPayload.CONFIRM_YES, 'title': '✅ Confirm Request'},
                {'id': AdmissionPayload.CONFIRM_NO, 'title': '❌ Cancel'}
            ]
        }, False
    
    # Invalid - show date buttons again
    gender = session.get_context('sex', '')
    return _get_date_selection_response(gender), False


def _handle_confirmation(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle confirmation button click."""
    
    # Handle text responses for legacy support
    if not is_button:
        response_lower = message.lower().strip()
        if response_lower in ['yes', 'y', 'confirm', 'ok']:
            message = AdmissionPayload.CONFIRM_YES
        elif response_lower in ['no', 'n', 'cancel']:
            message = AdmissionPayload.CONFIRM_NO
        else:
            return {
                'text': "Please tap a button to confirm or cancel:",
                'buttons': [
                    {'id': AdmissionPayload.CONFIRM_YES, 'title': '✅ Confirm Request'},
                    {'id': AdmissionPayload.CONFIRM_NO, 'title': '❌ Cancel'}
                ]
            }, False
    
    # CONFIRM
    if message == AdmissionPayload.CONFIRM_YES:
        ctx = session.context
        admission_id = _generate_admission_id()
        
        # Phone is automatically captured from WhatsApp user ID
        phone = session.user_id
        
        # Save to database with all details including date and phone
        saved = save_admission(
            admission_id=admission_id,
            user_id=session.user_id,
            patient_name=ctx.get('patient_name', ''),
            age=ctx.get('age'),
            sex=ctx.get('sex'),
            admission_type=ctx.get('admission_type', ''),
            preferred_date=ctx.get('preferred_date'),
            phone=phone,
            is_walkin=ctx.get('is_walkin', False)
        )
        
        if not saved:
            return {
                'text': "❌ Failed to save request. Please call reception: +91 98854 54128",
                'buttons': [
                    {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
                ]
            }, True
        
        # Build confirmation message based on type
        if ctx.get('is_walkin'):
            details_section = f"""🏥 Type: {ctx.get('admission_type', 'N/A')}
👤 Patient: Walk-in (Details at reception)
📱 Phone: {phone}"""
        else:
            details_section = f"""🏥 Type: {ctx.get('admission_type', 'N/A')}
👤 Name: {ctx.get('patient_name', 'N/A')}
🎂 Age: {ctx.get('age', 'N/A')} years
⚧ Gender: {ctx.get('sex', 'N/A')}
📅 Preferred Date: {ctx.get('preferred_date', 'To be confirmed')}
📱 Phone: {phone}"""
        
        confirmation = f"""✅ *Admission Request Confirmed!*

🆔 *Reference ID:* {admission_id}

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
{details_section}
━━━━━━━━━━━━━━━━━━━━━

*What's Next:*
Our team will contact you within 24 hours to discuss:
• Available rooms
• Admission date confirmation
• Required documents
• Estimated costs

━━━━━━━━━━━━━━━━━━━━━
📞 *Contact:* {clinic['phone']}
📍 *Location:* {clinic['address']}
━━━━━━━━━━━━━━━━━━━━━

Save your reference ID: *{admission_id}*"""
        
        logger.info(f"Admission request confirmed: {admission_id}")
        
        return {
            'text': confirmation,
            'buttons': [
                {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
            ]
        }, True
    
    # CANCEL
    if message == AdmissionPayload.CONFIRM_NO:
        return _get_cancelled_response(), True
    
    # Unknown - show confirmation buttons again
    return {
        'text': "Please confirm or cancel:",
        'buttons': [
            {'id': AdmissionPayload.CONFIRM_YES, 'title': '✅ Confirm Request'},
            {'id': AdmissionPayload.CONFIRM_NO, 'title': '❌ Cancel'}
        ]
    }, False


# =============================================================================
# RESPONSE BUILDER FUNCTIONS
# =============================================================================

def _get_admission_menu_response(intro_text: str = None) -> Dict[str, Any]:
    """Build admission type menu response."""
    
    body = intro_text or """*Hospital Admission* 🏥

Please select the type of admission:

🚨 *Emergency* - For urgent/critical care
🏥 *Planned* - For scheduled admission"""
    
    return {
        'text': body,
        'buttons': [
            {'id': AdmissionPayload.EMERGENCY, 'title': '🚨 Emergency'},
            {'id': AdmissionPayload.NON_EMERGENCY, 'title': '🏥 Planned Admission'}
        ],
        'footer': 'For emergencies, call +91 98854 54128'
    }


def _get_date_selection_response(context_info: str, intro_text: str = None) -> Dict[str, Any]:
    """Build date selection response with buttons."""
    
    dates = _get_available_dates()
    
    body = intro_text or f"""✅ Gender: *{context_info}*

━━━━━━━━━━━━━━━━━━━━━

*Select Preferred Admission Date:*

When would you like to be admitted?"""
    
    return {
        'text': body,
        'list': {
            'button_text': 'Select Date',
            'sections': [{
                'title': 'Available Dates',
                'rows': [
                    {
                        'id': f"{ADMISSION_DATE_PREFIX}{date['id']}", 
                        'title': date['display'][:24],
                        'description': date['day']
                    }
                    for date in dates
                ]
            }]
        }
    }


def _get_emergency_response(clinic: dict) -> Dict[str, Any]:
    """Build emergency admission response with call info."""
    
    body = f"""🚨 *EMERGENCY ADMISSION*

Your request has been received.

━━━━━━━━━━━━━━━━━━━━━
*PLEASE CALL IMMEDIATELY:*
━━━━━━━━━━━━━━━━━━━━━

📞 *Reception:* +91 98854 54128
📞 *Emergency:* +91 96741 08108

━━━━━━━━━━━━━━━━━━━━━

Our ICU and emergency teams are available *24x7*.

━━━━━━━━━━━━━━━━━━━━━
📍 *{clinic['name']}*
{clinic['address']}
━━━━━━━━━━━━━━━━━━━━━

_For life-threatening emergencies, please call 108 or proceed directly to the Emergency department._"""
    
    return {
        'text': body,
        'buttons': [
            {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
        ]
    }


def _get_cancelled_response() -> Dict[str, Any]:
    """Build cancellation response."""
    
    return {
        'text': "Admission request cancelled.\n\nWhat would you like to do?",
        'buttons': [
            {'id': MainMenuPayload.APPOINTMENT, 'title': '📅 Book Appointment'},
            {'id': MainMenuPayload.DIAGNOSTICS, 'title': '🧪 Diagnostics'},
            {'id': MainMenuPayload.ADMISSION, 'title': '🏥 Admission'}
        ]
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_available_dates() -> list:
    """Get next 7 available dates (excluding Sunday) with IDs."""
    dates = []
    current = datetime.now() + timedelta(days=1)
    
    while len(dates) < 7:
        if current.weekday() != 6:  # Skip Sunday
            dates.append({
                'id': current.strftime("%Y-%m-%d"),
                'display': current.strftime("%d %b %Y"),
                'day': current.strftime("%A")
            })
        current += timedelta(days=1)
    
    return dates


def _generate_admission_id() -> str:
    """Generate unique admission ID."""
    import random
    import string
    timestamp = datetime.now().strftime("%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"ADM{timestamp}{random_part}"
