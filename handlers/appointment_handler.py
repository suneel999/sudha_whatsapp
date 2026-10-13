"""
Text-Based Appointment Handler - Button-Based Fallback

=============================================================================
ENTERPRISE-GRADE BUTTON ROUTING
=============================================================================

This handler is used as a FALLBACK when WhatsApp Flows are disabled.
The primary appointment booking uses WhatsApp Flow (via /flow endpoint).

FLOW (SIMPLIFIED - NO PHONE INPUT):
1. SELECT_DOCTOR: User clicks doctor button
2. SELECT_DATE: User clicks date button (7 available dates)
3. SELECT_TIME: User clicks time button (6 time slots)
4. ENTER_NAME: User types patient name
5. CONFIRM: User clicks confirm/cancel button

Phone number is automatically captured from WhatsApp - no need to ask!

=============================================================================
"""

import logging
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta

from state_machine import Session, SubState
from button_payloads import (
    AppointmentPayload, GlobalPayload, MainMenuPayload,
    DOCTOR_PAYLOAD_MAP
)
from database import save_appointment

logger = logging.getLogger(__name__)

# Date and Time payload prefixes
APT_DATE_PREFIX = "APT_DATE_"
APT_TIME_PREFIX = "APT_TIME_"


def handle_text_appointment(
    session: Session,
    message: str,
    clinic: dict,
    clinic_id: str,
    is_button: bool = False
) -> Tuple[Dict[str, Any], bool]:
    """
    Handle text-based appointment booking (fallback for disabled Flows).
    
    Phone number is automatically captured from user_id (WhatsApp number).
    """
    sub_state = session.sub_state
    
    logger.info(f"Text appointment handler - SubState: {sub_state}, "
                f"Message: {message[:30]}, IsButton: {is_button}")
    
    # Handle global navigation
    if message in [AppointmentPayload.BACK_TO_MENU, GlobalPayload.MAIN_MENU, GlobalPayload.CANCEL]:
        return _get_cancelled_response(), True
    
    # Route to appropriate sub-state
    if sub_state == SubState.SELECT_DOCTOR.value:
        return _handle_doctor_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_DATE.value:
        return _handle_date_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.SELECT_TIME.value:
        return _handle_time_selection(session, message, clinic, is_button)
    
    elif sub_state == SubState.ENTER_NAME.value:
        return _handle_name_input(session, message, clinic, is_button)
    
    elif sub_state == SubState.ENTER_PHONE.value:
        return _handle_phone_input(session, message, clinic, is_button)

    elif sub_state == SubState.CONFIRM.value:
        return _handle_confirmation(session, message, clinic, clinic_id, is_button)
    
    # Unknown - show doctor selection
    session.set_sub_state(SubState.SELECT_DOCTOR)
    return _get_doctor_menu_response(), False


def _handle_doctor_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle doctor selection via button."""
    
    # Only accept button clicks
    if not is_button:
        return _get_doctor_menu_response(
            "Please tap a button to select a doctor:"
        ), False
    
    # Check valid doctor payload
    if message in DOCTOR_PAYLOAD_MAP:
        doctor = DOCTOR_PAYLOAD_MAP[message]
        
        session.set_context('doctor_id', doctor['id'])
        session.set_context('doctor_name', doctor['name'])
        session.set_context('doctor_specialty', doctor['specialty'])
        session.set_sub_state(SubState.SELECT_DATE)
        
        logger.info(f"Appointment: Doctor selected - {doctor['name']}")
        
        return _get_date_selection_response(doctor['name'], doctor['specialty']), False
    
    # Invalid - show doctor menu
    return _get_doctor_menu_response(), False


def _handle_date_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle date selection via button or text 'more' for list of dates."""
    
    doctor_name = session.get_context('doctor_name', '')
    specialty = session.get_context('doctor_specialty', '')
    
    if not is_button:
        if message.strip().lower() in ('more', 'more dates', 'more options'):
            return _get_date_list_response(doctor_name, specialty), False
        return _get_date_selection_response(doctor_name, specialty,
            "Please tap a button to select your preferred date:"), False
    
    # "More dates" button – show full list
    if message == AppointmentPayload.MORE_DATES:
        return _get_date_list_response(doctor_name, specialty), False
    
    # Date payload selected
    if message.startswith(APT_DATE_PREFIX):
        date_str = message.replace(APT_DATE_PREFIX, '')
        
        session.set_context('date', date_str)
        session.set_sub_state(SubState.SELECT_TIME)
        
        logger.info(f"Appointment: Date selected - {date_str}")
        
        return _get_time_selection_response(date_str), False
    
    # Invalid – show date buttons again
    return _get_date_selection_response(doctor_name, specialty), False


def _handle_time_selection(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle time selection via button or 'more' for afternoon slots."""
    
    date_str = session.get_context('date', '')
    
    if not is_button:
        if message.strip().lower() in ('more', 'afternoon', 'more times'):
            return _get_time_more_response(date_str), False
        return _get_time_selection_response(date_str,
            "Please tap a button to select your preferred time:"), False
    
    # "More times" button – show afternoon slots
    if message == AppointmentPayload.MORE_TIMES:
        return _get_time_more_response(date_str), False
    
    # Time payload selected
    if message.startswith(APT_TIME_PREFIX):
        time_str = message.replace(APT_TIME_PREFIX, '').replace('_', ' ')
        
        session.set_context('time', time_str)
        session.set_sub_state(SubState.ENTER_NAME)
        
        logger.info(f"Appointment: Time selected - {time_str}")
        
        return {
            'text': f"""✅ Time: *{time_str}*

━━━━━━━━━━━━━━━━━━━━━

*Enter Patient Name:*
Please type the full name of the patient:"""
        }, False
    
    # Invalid - show time buttons again
    date_str = session.get_context('date', '')
    return _get_time_selection_response(date_str), False


def _is_non_whatsapp_user(user_id: str) -> bool:
    """Return True for Instagram/Facebook session IDs."""
    uid = str(user_id or '')
    return uid.startswith('instagram_') or uid.startswith('facebook_')


def _build_confirmation_summary(ctx: dict, patient_name: str, phone: str = None) -> str:
    """Build confirmation text with optional phone line."""
    phone_line = f"\nPhone: {phone}" if phone else ""
    return f"""Confirm Your Appointment

Appointment Details:
Doctor: {ctx.get('doctor_name', 'N/A')}
Specialty: {ctx.get('doctor_specialty', 'N/A')}
Date: {ctx.get('date', 'N/A')}
Time: {ctx.get('time', 'N/A')}
Patient: {patient_name}{phone_line}

Please confirm your appointment:"""


def _handle_name_input(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Handle patient name text input."""

    if is_button:
        return {
            'text': "Please *type* the patient's name:"
        }, False

    name = message.strip()

    if len(name) < 2:
        return {
            'text': "Name too short. Please enter a valid name (at least 2 characters):"
        }, False

    if len(name) > 100:
        return {
            'text': "Name too long. Please enter a shorter name:"
        }, False

    if any(char.isdigit() for char in name):
        return {
            'text': "Name should not contain numbers. Please enter a valid name:"
        }, False

    session.set_context('patient_name', name)

    # Instagram/Facebook users do not have phone-number user IDs, so collect phone explicitly.
    if _is_non_whatsapp_user(session.user_id):
        session.set_sub_state(SubState.ENTER_PHONE)
        return {
            'text': "Please enter patient's contact phone number (minimum 10 digits):"
        }, False

    # WhatsApp fallback: auto-use sender number.
    session.set_context('phone', session.user_id)
    session.set_sub_state(SubState.CONFIRM)

    return {
        'text': _build_confirmation_summary(session.context, name),
        'buttons': [
            {'id': AppointmentPayload.CONFIRM_YES, 'title': 'Confirm'},
            {'id': AppointmentPayload.CONFIRM_NO, 'title': 'Cancel'}
        ]
    }, False


def _handle_phone_input(
    session: Session,
    message: str,
    clinic: dict,
    is_button: bool
) -> Tuple[Dict[str, Any], bool]:
    """Collect phone input for Instagram/Facebook appointment fallback."""

    if is_button:
        return {
            'text': "Please type the phone number (minimum 10 digits):"
        }, False

    phone = message.strip().replace(' ', '').replace('-', '')
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return {
            'text': "Invalid phone. Please enter at least 10 digits:"
        }, False

    session.set_context('phone', phone)
    session.set_sub_state(SubState.CONFIRM)

    return {
        'text': _build_confirmation_summary(session.context, session.get_context('patient_name', 'N/A'), phone),
        'buttons': [
            {'id': AppointmentPayload.CONFIRM_YES, 'title': 'Confirm'},
            {'id': AppointmentPayload.CONFIRM_NO, 'title': 'Cancel'}
        ]
    }, False

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
            message = AppointmentPayload.CONFIRM_YES
        elif response_lower in ['no', 'n', 'cancel']:
            message = AppointmentPayload.CONFIRM_NO
        else:
            return {
                'text': "Please tap a button to confirm or cancel:",
                'buttons': [
                    {'id': AppointmentPayload.CONFIRM_YES, 'title': '✅ Confirm'},
                    {'id': AppointmentPayload.CONFIRM_NO, 'title': '❌ Cancel'}
                ]
            }, False
    
    # CONFIRM
    if message == AppointmentPayload.CONFIRM_YES:
        ctx = session.context
        booking_id = _generate_booking_id()
        
        # WhatsApp auto-uses sender; Instagram/Facebook uses collected phone.
        phone = ctx.get('phone', session.user_id)
        
        saved = save_appointment(
            booking_id=booking_id,
            user_id=session.user_id,
            patient_name=ctx.get('patient_name', ''),
            department=ctx.get('doctor_specialty', ''),
            department_name=ctx.get('doctor_specialty', ''),
            doctor=ctx.get('doctor_name', ''),
            date=ctx.get('date', ''),
            time_slot=ctx.get('time', ''),
            clinic_id=clinic_id,
            phone=phone
        )
        
        if not saved:
            return {
                'text': "❌ Failed to save appointment. Please try again or call reception.",
                'buttons': [
                    {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
                ]
            }, True
        
        confirmation = f"""✅ *Appointment Confirmed!*

🆔 *Booking ID:* {booking_id}

━━━━━━━━━━━━━━━━━━━━━
*Appointment Details:*
━━━━━━━━━━━━━━━━━━━━━
👨‍⚕️ Doctor: {ctx.get('doctor_name', 'N/A')}
🏥 Specialty: {ctx.get('doctor_specialty', 'N/A')}
📅 Date: {ctx.get('date', 'N/A')}
⏰ Time: {ctx.get('time', 'N/A')}
👤 Patient: {ctx.get('patient_name', 'N/A')}
📱 Phone: {phone}
━━━━━━━━━━━━━━━━━━━━━

📍 *Location:* {clinic['address']}
📞 *Contact:* {clinic['phone']}
🌐 *Website:* {clinic.get('website', 'mallikahospitals.in')}

_Please arrive 15 minutes before your appointment._

Save your booking ID: *{booking_id}*
Need to cancel? Reply: *cancel {booking_id}*"""
        
        logger.info(f"Appointment confirmed: {booking_id}")
        
        return {
            'text': confirmation,
            'buttons': [
                {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
            ]
        }, True
    
    # CANCEL
    if message == AppointmentPayload.CONFIRM_NO:
        return _get_cancelled_response(), True
    
    # Unknown - show confirmation buttons
    return {
        'text': "Please confirm or cancel:",
        'buttons': [
            {'id': AppointmentPayload.CONFIRM_YES, 'title': '✅ Confirm'},
            {'id': AppointmentPayload.CONFIRM_NO, 'title': '❌ Cancel'}
        ]
    }, False


# =============================================================================
# RESPONSE BUILDER FUNCTIONS
# =============================================================================

def _get_doctor_menu_response(intro_text: str = None) -> Dict[str, Any]:
    """Build doctor selection menu."""
    
    body = intro_text or """*Book Appointment* 📅

Please select a doctor:"""
    
    return {
        'text': body,
        'buttons': [
            {'id': AppointmentPayload.DR_MAHESH, 'title': '🫀 Dr. Mahesh Babu'},
            {'id': AppointmentPayload.DR_MOUNIKA, 'title': '🧠 Dr. Mounika Reddy'},
            {'id': AppointmentPayload.DR_RAHUL, 'title': '🦴 Dr. Rahul'}
        ],
        'footer': 'Select your preferred doctor'
    }


def _get_date_selection_response(doctor_name: str, specialty: str, intro_text: str = None) -> Dict[str, Any]:
    """
    Date selection: always show 3 BUTTONS first (so user always sees tappable options).
    Say 'more' to get the full list (up to 3 months).
    """
    dates = _get_available_dates(doctor_name=doctor_name)
    
    body = intro_text or f"""✅ *{doctor_name}*
{specialty}

*Select a date* (tap one below):"""
    
    if not dates:
        return {
            'text': body + "\n\nNo dates available. Please try again later.",
            'buttons': [{'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}]
        }
    
    # 2 date buttons + 1 "More dates" button (WhatsApp max 3 buttons)
    two_dates = [
        {'id': f"{APT_DATE_PREFIX}{d['id']}", 'title': d['display'][:20]}
        for d in dates[:2]
    ]
    two_dates.append({'id': AppointmentPayload.MORE_DATES, 'title': '📅 More dates'})
    return {
        'text': body,
        'buttons': two_dates,
        'footer': 'Tap "More dates" for full list (up to 3 months)'
    }


def _get_date_list_response(doctor_name: str, specialty: str) -> Dict[str, Any]:
    """Full date list (when user says 'more'). Meta: 10 rows/section, 10 sections max."""
    dates = _get_available_dates(doctor_name=doctor_name)
    body = f"""✅ *{doctor_name}*

*Select a date* – tap the button below:"""
    
    if not dates:
        return _get_date_selection_response(doctor_name, specialty)
    
    ROWS_PER_SECTION = 10
    MAX_SECTIONS = 10
    sections = []
    for i in range(0, min(len(dates), ROWS_PER_SECTION * MAX_SECTIONS), ROWS_PER_SECTION):
        chunk = dates[i:i + ROWS_PER_SECTION]
        first_date, last_date = chunk[0], chunk[-1]
        section_title = f"{first_date['display']} - {last_date['display']}"[:24]
        sections.append({
            'title': section_title,
            'rows': [
                {
                    'id': f"{APT_DATE_PREFIX}{d['id']}",
                    'title': d['display'][:24],
                    'description': d['day'][:72]
                }
                for d in chunk
            ]
        })
    
    return {
        'text': body,
        'list': {
            'button_text': 'Select Date',
            'sections': sections
        },
        'footer': f'{len(dates)} dates'
    }


def _get_time_selection_response(date_str: str, intro_text: str = None) -> Dict[str, Any]:
    """Time selection: use BUTTONS so user always sees tappable options (max 3)."""
    
    body = intro_text or f"""✅ Date: *{date_str}*

*Select a time* (tap one below):"""
    
    time_slots = _get_time_slots()
    # 2 time buttons + 1 "More times" button (WhatsApp max 3)
    two_times = [
        {'id': f"{APT_TIME_PREFIX}{s['id']}", 'title': s['display'][:20]}
        for s in time_slots[:2]
    ]
    two_times.append({'id': AppointmentPayload.MORE_TIMES, 'title': '🕐 More times'})
    return {
        'text': body,
        'buttons': two_times,
        'footer': 'Tap "More times" for afternoon slots'
    }


def _get_time_more_response(date_str: str) -> Dict[str, Any]:
    """Afternoon time slots (when user says 'more')."""
    time_slots = _get_time_slots()
    afternoon = [
        {'id': f"{APT_TIME_PREFIX}{s['id']}", 'title': s['display'][:20]}
        for s in time_slots[3:6]
    ]
    body = f"""✅ Date: *{date_str}*

*Afternoon slots* (tap one):"""
    if afternoon:
        return {'text': body, 'buttons': afternoon}
    return _get_time_selection_response(date_str)


def _get_cancelled_response() -> Dict[str, Any]:
    """Build cancellation response."""
    
    return {
        'text': "Appointment booking cancelled.\n\nWhat would you like to do?",
        'buttons': [
            {'id': MainMenuPayload.APPOINTMENT, 'title': '📅 Book Appointment'},
            {'id': MainMenuPayload.DIAGNOSTICS, 'title': '🧪 Diagnostics'},
            {'id': MainMenuPayload.ADMISSION, 'title': '🏥 Admission'}
        ]
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_available_dates(doctor_name: str = None) -> list:
    """Get available dates up to 3 months. Dr. Mahesh: no Thu/Sun; other doctors: no Sun. Max 90 dates (fits 9 sections of 10)."""
    dates = []
    current = datetime.now() + timedelta(days=1)
    end = current + timedelta(days=92)  # ~3 months
    is_dr_mahesh = doctor_name and ('mahesh' in (doctor_name or '').lower())
    
    while current < end and len(dates) < 90:
        wd = current.weekday()  # 0 Mon .. 6 Sun
        skip = False
        if wd == 6:
            skip = True  # Sunday: all doctors
        elif is_dr_mahesh and wd == 3:
            skip = True  # Thursday: Dr. Mahesh only
        if not skip:
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
    return f"APT{timestamp}{random_part}"
