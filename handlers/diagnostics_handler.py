"""
Diagnostics Flow Handler - Button-Based Diagnostic Test Booking

=============================================================================
ENTERPRISE-GRADE BUTTON ROUTING
=============================================================================

This handler processes diagnostic test bookings using ONLY buttons.

FLOW (SIMPLIFIED - NO PHONE INPUT):
1. SELECT_TEST: User clicks test button (DIAG_ECG, DIAG_4DECHO, etc.)
2. ENTER_NAME: User types patient name (text input)
3. SELECT_DATE: User clicks date button (7 available dates)
4. SELECT_TIME: User clicks time button (6 time slots)
5. CONFIRM: User clicks confirm/cancel button

Phone number is automatically captured from WhatsApp - no need to ask!

=============================================================================
"""

import logging
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

from state_machine import Session, SubState
from button_payloads import (
    DiagnosticsPayload, GlobalPayload,
    DIAGNOSTICS_PAYLOAD_MAP
)
from database import save_diagnostic

logger = logging.getLogger(__name__)

# Date and Time payload prefixes
DATE_PAYLOAD_PREFIX = "DIAG_DATE_"
TIME_PAYLOAD_PREFIX = "DIAG_TIME_"


def handle_diagnostics_flow(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False
) -> Tuple[Dict[str, Any], bool]:
    """
    Handle diagnostic test booking flow.
    
    Phone number is automatically captured from user_id (WhatsApp number).
    No need to ask for phone - it's already available!
    """
    sub_state = session.sub_state
    
    logger.info(f"Diagnostics handler - SubState: {sub_state}, "
                f"Message: {message[:30]}, IsButton: {is_button}")
    
    # Handle global navigation payloads
    if message == DiagnosticsPayload.BACK_TO_MENU or message == GlobalPayload.MAIN_MENU:
        return _get_cancelled_response(), True
    
    if message == GlobalPayload.CANCEL:
        return _get_cancelled_response(), True
    
    # Route to appropriate sub-state handler
    if sub_state == SubState.SELECT_TEST.value:
        return _handle_test_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.ENTER_NAME.value:
        return _handle_name_input(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_DATE.value:
        return _handle_date_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_TIME.value:
        return _handle_time_selection(session, message, clinic, clinic_id, is_button)
    
    elif sub_state == SubState.CONFIRM.value:
        return _handle_confirmation(session, message, clinic, clinic_id, is_button)
    
    # Unknown sub-state - show test selection
    session.set_sub_state(SubState.SELECT_TEST)
    return _get_test_menu_response(), False


def _handle_test_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle diagnostic test selection via button payload."""
    
    # Only accept button clicks for test selection
    if not is_button:
        return _get_test_menu_response(
            "Please tap a button below to select your test:"
        ), False
    
    # Check if it's a valid diagnostic payload
    if message in DIAGNOSTICS_PAYLOAD_MAP:
        test = DIAGNOSTICS_PAYLOAD_MAP[message]
        
        # Save test selection
        session.set_context('test_type', test['id'])
        session.set_context('test_name', test['name'])
        session.set_context('test_description', test['description'])
        session.set_sub_state(SubState.ENTER_NAME)
        
        logger.info(f"Diagnostics: Test selected via button - {test['name']}")
        
        return {
            'text': f"""✅ Selected: *{test['name']}*
_{test['description']}_

━━━━━━━━━━━━━━━━━━━━━

*Enter Patient Name:*
Please type the full name of the patient."""
        }, False
    
    # Invalid payload - show test menu
    return _get_test_menu_response(
        "Please select a test from the list:"
    ), False


def _handle_name_input(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle patient name text input."""
    
    # Name must be text input, not button
    if is_button:
        return {
            'text': "Please *type* the patient's name:",
            'footer': "Example: Ravi Kumar"
        }, False
    
    name = message.strip()
    
    # Validate name
    if len(name) < 2:
        return {
            'text': "❌ Name too short.\n\nPlease enter a valid name (at least 2 characters):"
        }, False
    
    if len(name) > 100:
        return {
            'text': "❌ Name too long.\n\nPlease enter a shorter name:"
        }, False
    
    if any(char.isdigit() for char in name):
        return {
            'text': "❌ Name should not contain numbers.\n\nPlease enter a valid name:"
        }, False
    
    # Save name and move to date selection
    session.set_context('patient_name', name)
    session.set_sub_state(SubState.SELECT_DATE)
    
    return _get_date_selection_response(name), False


def _handle_date_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle date selection via button."""
    
    # Only accept button clicks for date selection
    if not is_button:
        patient_name = session.get_context('patient_name', '')
        return _get_date_selection_response(patient_name, 
            "Please tap a button to select your preferred date:"), False
    
    # Check if it's a date payload
    if message.startswith(DATE_PAYLOAD_PREFIX):
        date_str = message.replace(DATE_PAYLOAD_PREFIX, '')
        
        session.set_context('date', date_str)
        session.set_sub_state(SubState.SELECT_TIME)
        
        logger.info(f"Diagnostics: Date selected - {date_str}")
        
        return _get_time_selection_response(date_str), False
    
    # Invalid - show date buttons again
    patient_name = session.get_context('patient_name', '')
    return _get_date_selection_response(patient_name), False


def _handle_time_selection(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle time selection via button - then go directly to confirmation."""
    
    # Only accept button clicks for time selection
    if not is_button:
        date_str = session.get_context('date', '')
        return _get_time_selection_response(date_str,
            "Please tap a button to select your preferred time:"), False
    
    # Check if it's a time payload
    if message.startswith(TIME_PAYLOAD_PREFIX):
        time_str = message.replace(TIME_PAYLOAD_PREFIX, '').replace('_', ' ')
        
        session.set_context('time', time_str)
        # Phone is automatically the user's WhatsApp number (session.user_id)
        session.set_context('phone', session.user_id)
        session.set_sub_state(SubState.CONFIRM)
        
        logger.info(f"Diagnostics: Time selected - {time_str}")
        
        # Show confirmation directly (skip phone input)
        ctx = session.context
        
        summary = f"""*Confirm Diagnostic Booking*

━━━━━━━━━━━━━━━━━━━━━
*Booking Details:*
━━━━━━━━━━━━━━━━━━━━━
🧪 Test: {ctx.get('test_name', 'N/A')}
👤 Patient: {ctx.get('patient_name', 'N/A')}
📅 Date: {ctx.get('date', 'N/A')}
⏰ Time: {time_str}
━━━━━━━━━━━━━━━━━━━━━

Please confirm your booking:"""
        
        return {
            'text': summary,
            'buttons': [
                {'id': DiagnosticsPayload.CONFIRM_YES, 'title': '✅ Confirm Booking'},
                {'id': DiagnosticsPayload.CONFIRM_NO, 'title': '❌ Cancel'}
            ]
        }, False
    
    # Invalid - show time buttons again
    date_str = session.get_context('date', '')
    return _get_time_selection_response(date_str), False


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
            message = DiagnosticsPayload.CONFIRM_YES
        elif response_lower in ['no', 'n', 'cancel']:
            message = DiagnosticsPayload.CONFIRM_NO
        else:
            return {
                'text': "Please tap a button to confirm or cancel:",
                'buttons': [
                    {'id': DiagnosticsPayload.CONFIRM_YES, 'title': '✅ Confirm Booking'},
                    {'id': DiagnosticsPayload.CONFIRM_NO, 'title': '❌ Cancel'}
                ]
            }, False
    
    # CONFIRM
    if message == DiagnosticsPayload.CONFIRM_YES:
        ctx = session.context
        booking_id = _generate_booking_id()
        
        # Phone is the user's WhatsApp number
        phone = session.user_id
        
        # Save to database
        saved = save_diagnostic(
            booking_id=booking_id,
            user_id=session.user_id,
            patient_name=ctx.get('patient_name', ''),
            test_type=ctx.get('test_name', ''),
            date=ctx.get('date', ''),
            time_slot=ctx.get('time', ''),
            phone=phone
        )
        
        if not saved:
            return {
                'text': "❌ Failed to save booking. Please try again or call reception.",
                'buttons': [
                    {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
                ]
            }, True
        
        confirmation = f"""✅ *Diagnostic Test Confirmed!*

🆔 *Booking ID:* {booking_id}

━━━━━━━━━━━━━━━━━━━━━
*Booking Details:*
━━━━━━━━━━━━━━━━━━━━━
🧪 Test: {ctx.get('test_name', 'N/A')}
👤 Patient: {ctx.get('patient_name', 'N/A')}
📅 Date: {ctx.get('date', 'N/A')}
⏰ Time: {ctx.get('time', 'N/A')}
📱 Phone: {phone}
━━━━━━━━━━━━━━━━━━━━━

📍 *Location:* {clinic['address']}
📞 *Contact:* {clinic['phone']}
🌐 *Website:* {clinic.get('website', 'mallikahospitals.in')}

━━━━━━━━━━━━━━━━━━━━━
*Instructions:*
━━━━━━━━━━━━━━━━━━━━━
• Please arrive 15 minutes early
• Bring previous reports if available
• Follow fasting instructions if applicable

Save your booking ID: *{booking_id}*"""
        
        logger.info(f"Diagnostic booking confirmed: {booking_id}")
        
        return {
            'text': confirmation,
            'buttons': [
                {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
            ]
        }, True
    
    # CANCEL
    if message == DiagnosticsPayload.CONFIRM_NO:
        return _get_cancelled_response(), True
    
    # Unknown - show confirmation buttons again
    return {
        'text': "Please confirm or cancel your booking:",
        'buttons': [
            {'id': DiagnosticsPayload.CONFIRM_YES, 'title': '✅ Confirm Booking'},
            {'id': DiagnosticsPayload.CONFIRM_NO, 'title': '❌ Cancel'}
        ]
    }, False


# =============================================================================
# RESPONSE BUILDER FUNCTIONS
# =============================================================================

def _get_test_menu_response(intro_text: str = None) -> Dict[str, Any]:
    """Build diagnostic test menu response."""
    
    body = intro_text or """*Book Diagnostic Test* 🧪

Select the test you need from the list below.

Our diagnostic center features:
• 4D ECHO (GE VIVID E95)
• Advanced Cath Lab
• Fully Automated Laboratory"""
    
    return {
        'text': body,
        'list': {
            'button_text': 'Select Test',
            'sections': [{
                'title': 'Available Tests',
                'rows': [
                    {'id': DiagnosticsPayload.ECG, 'title': 'ECG', 'description': 'Heart rhythm test'},
                    {'id': DiagnosticsPayload.ECHO_4D, 'title': '4D ECHO', 'description': '4D Echocardiography'},
                    {'id': DiagnosticsPayload.TMT, 'title': 'TMT', 'description': 'Treadmill stress test'},
                    {'id': DiagnosticsPayload.ANGIOGRAM, 'title': 'Coronary Angiogram', 'description': 'Heart vessel imaging'},
                    {'id': DiagnosticsPayload.MRI, 'title': 'MRI', 'description': 'Magnetic Resonance'},
                    {'id': DiagnosticsPayload.CT_SCAN, 'title': 'CT Scan', 'description': 'Computed Tomography'},
                    {'id': DiagnosticsPayload.BLOOD, 'title': 'Blood Investigation', 'description': 'Complete blood panel'}
                ]
            }]
        },
        'footer': 'Tap to view options'
    }


def _get_date_selection_response(patient_name: str, intro_text: str = None) -> Dict[str, Any]:
    """Build date selection response with buttons."""
    
    dates = _get_available_dates()
    
    body = intro_text or f"""✅ Patient: *{patient_name}*

━━━━━━━━━━━━━━━━━━━━━

*Select Preferred Date:*

Tap a button to choose your date:"""
    
    return {
        'text': body,
        'list': {
            'button_text': 'Select Date',
            'sections': [{
                'title': 'Available Dates',
                'rows': [
                    {
                        'id': f"{DATE_PAYLOAD_PREFIX}{date['id']}", 
                        'title': date['display'][:24],
                        'description': date['day']
                    }
                    for date in dates
                ]
            }]
        }
    }


def _get_time_selection_response(date_str: str, intro_text: str = None) -> Dict[str, Any]:
    """Build time selection response with buttons."""
    
    body = intro_text or f"""✅ Date: *{date_str}*

━━━━━━━━━━━━━━━━━━━━━

*Select Preferred Time:*

Tap a button to choose your time:"""
    
    time_slots = _get_time_slots()
    
    return {
        'text': body,
        'list': {
            'button_text': 'Select Time',
            'sections': [{
                'title': 'Morning Slots',
                'rows': [
                    {
                        'id': f"{TIME_PAYLOAD_PREFIX}{slot['id']}", 
                        'title': slot['display'],
                        'description': 'Morning appointment'
                    }
                    for slot in time_slots[:3]
                ]
            }, {
                'title': 'Afternoon Slots',
                'rows': [
                    {
                        'id': f"{TIME_PAYLOAD_PREFIX}{slot['id']}", 
                        'title': slot['display'],
                        'description': 'Afternoon appointment'
                    }
                    for slot in time_slots[3:]
                ]
            }]
        }
    }


def _get_cancelled_response() -> Dict[str, Any]:
    """Build cancellation response."""
    from button_payloads import MainMenuPayload
    
    return {
        'text': "Diagnostic booking cancelled.\n\nWhat would you like to do?",
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
    """Get available dates up to 3 months (excluding Sunday)."""
    dates = []
    current = datetime.now() + timedelta(days=1)
    end = current + timedelta(days=92)
    
    while current < end and len(dates) < 31:
        if current.weekday() != 6:  # Skip Sunday
            dates.append({
                'id': current.strftime("%Y-%m-%d"),
                'display': current.strftime("%d %b"),
                'day': current.strftime("%A")
            })
        current += timedelta(days=1)
    
    return dates


def _get_time_slots() -> list:
    """Get available time slots with IDs."""
    return [
        {'id': '09_00_AM', 'display': '09:00 AM'},
        {'id': '10_00_AM', 'display': '10:00 AM'},
        {'id': '11_00_AM', 'display': '11:00 AM'},
        {'id': '02_00_PM', 'display': '02:00 PM'},
        {'id': '03_00_PM', 'display': '03:00 PM'},
        {'id': '04_00_PM', 'display': '04:00 PM'},
    ]


def _generate_booking_id() -> str:
    """Generate unique booking ID."""
    import random
    import string
    timestamp = datetime.now().strftime("%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"DGN{timestamp}{random_part}"
