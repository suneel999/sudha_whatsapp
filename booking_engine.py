"""
Booking Engine
Handles three types of bookings:
1. Appointments - Doctor consultations (can use WhatsApp Flow or text-based)
2. Diagnostics - Lab tests and scans (text-based flow)
3. Admissions - Hospital admissions (text-based flow)

100% deterministic - NO AI involvement.
Database-backed session management.
"""

import random
import string
import logging
from typing import Tuple
from datetime import datetime, timedelta

from config import get_clinic_config, get_diagnostics_tests, get_admission_types
from session_manager import (
    BookingSession, get_session, create_session,
    update_session, delete_session
)
from database import (
    save_appointment, get_appointment, cancel_appointment as db_cancel,
    save_diagnostic, get_diagnostic,
    save_admission, get_admission
)

logger = logging.getLogger(__name__)


# ============================================================================
# APPOINTMENT FLOW (Text-based fallback when WhatsApp Flow is unavailable)
# ============================================================================

def start_appointment_flow(user_id: str, clinic_id: str = None) -> Tuple[str, bool]:
    """
    Start appointment booking flow (text-based).
    Used when WhatsApp Flows are not available.
    """
    # Clear any existing session
    existing = get_session(user_id)
    if existing:
        delete_session(user_id)
    
    # Create new appointment session
    session = create_session(user_id, 'appointment')
    clinic = get_clinic_config(clinic_id)
    
    # Get doctors list
    doctors = clinic.get('appointment_doctors', [])
    if not doctors:
        doctors = [
            {"id": "dr_mahesh", "name": "Dr. Mahesh Babu", "specialty": "Cardiology"},
            {"id": "dr_mounika", "name": "Dr. Mounika Reddy", "specialty": "Neurology"},
            {"id": "dr_rahul", "name": "Dr. Rahul", "specialty": "Orthopedics"}
        ]
    
    # Build doctor selection message
    doctor_lines = []
    for i, doc in enumerate(doctors, 1):
        doctor_lines.append(f"*{i}* - {doc['name']} ({doc['specialty']})")
    
    message = f"""*Book Appointment*

Please select a doctor:

{chr(10).join(doctor_lines)}

Reply with the *number* of your choice.
Type *cancel* anytime to stop."""
    
    logger.info(f"Started appointment flow for user {user_id[:6]}***")
    return message, True


def process_booking_input(user_id: str, user_input: str, clinic_id: str = None) -> Tuple[str, bool]:
    """
    Process user input during appointment booking flow.
    
    Returns:
        Tuple of (message, is_flow_complete)
    """
    session = get_session(user_id)
    if not session:
        return "No active booking session. Type *1* to book an appointment.", True
    
    clinic = get_clinic_config(clinic_id)
    user_input = user_input.strip()
    
    # Handle cancel command
    if user_input.lower() in ['cancel', 'stop', 'exit', 'quit', 'menu']:
        delete_session(user_id)
        return "Booking cancelled. Type *menu* to return to main menu.", True
    
    step = session.step
    
    handlers = {
        'doctor': _handle_appointment_doctor,
        'date': _handle_appointment_date,
        'time': _handle_appointment_time,
        'patient_name': _handle_appointment_name,
        'phone': _handle_appointment_phone,
        'confirm': _handle_appointment_confirm
    }
    
    handler = handlers.get(step)
    if handler:
        return handler(session, user_input, clinic, clinic_id)
    
    delete_session(user_id)
    return "Something went wrong. Type *1* to start again.", True


def _handle_appointment_doctor(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle doctor selection."""
    try:
        doctors = clinic.get('appointment_doctors', [
            {"id": "dr_mahesh", "name": "Dr. Mahesh Babu", "specialty": "Cardiology"},
            {"id": "dr_mounika", "name": "Dr. Mounika Reddy", "specialty": "Neurology"},
            {"id": "dr_rahul", "name": "Dr. Rahul", "specialty": "Orthopedics"}
        ])
        
        choice = int(user_input)
        if 1 <= choice <= len(doctors):
            doc = doctors[choice - 1]
            session.set_value('doctor_id', doc['id'])
            session.set_value('doctor_name', doc['name'])
            session.set_value('doctor_specialty', doc['specialty'])
            session.next_step()
            update_session(session)
            
            # Build date selection
            dates = _get_available_dates()
            date_lines = [f"*{i}* - {d}" for i, d in enumerate(dates, 1)]
            
            return f"""Selected: *{doc['name']}* ({doc['specialty']})

*Select Date:*

{chr(10).join(date_lines)}

Reply with the *number*.""", False
        else:
            return f"Please enter a number between 1 and {len(doctors)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_appointment_date(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle date selection."""
    try:
        dates = _get_available_dates()
        choice = int(user_input)
        
        if 1 <= choice <= len(dates):
            selected_date = dates[choice - 1]
            session.set_value('date', selected_date)
            session.next_step()
            update_session(session)
            
            # Build time selection
            slots = clinic.get('time_slots', [
                "09:00 AM", "10:00 AM", "11:00 AM",
                "02:00 PM", "03:00 PM", "04:00 PM"
            ])
            slot_lines = [f"*{i}* - {s}" for i, s in enumerate(slots, 1)]
            
            return f"""Selected: *{selected_date}*

*Select Time:*

{chr(10).join(slot_lines)}

Reply with the *number*.""", False
        else:
            return f"Please enter a number between 1 and {len(dates)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_appointment_time(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle time slot selection."""
    try:
        slots = clinic.get('time_slots', [
            "09:00 AM", "10:00 AM", "11:00 AM",
            "02:00 PM", "03:00 PM", "04:00 PM"
        ])
        choice = int(user_input)
        
        if 1 <= choice <= len(slots):
            session.set_value('time', slots[choice - 1])
            session.next_step()
            update_session(session)
            
            return f"""Selected: *{slots[choice - 1]}*

*Enter Patient Name:*
Please enter the full name of the patient.""", False
        else:
            return f"Please enter a number between 1 and {len(slots)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_appointment_name(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle patient name collection."""
    name = user_input.strip()
    
    if len(name) < 2:
        return "Please enter a valid name (at least 2 characters).", False
    if len(name) > 100:
        return "Name is too long. Please enter a shorter name.", False
    if any(char.isdigit() for char in name):
        return "Name should not contain numbers.", False
    
    session.set_value('patient_name', name)
    session.next_step()
    update_session(session)
    
    return f"""Patient: *{name}*

*Enter Phone Number:*
Please enter the contact phone number.""", False


def _handle_appointment_phone(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle phone number collection."""
    phone = user_input.strip().replace(' ', '').replace('-', '')
    
    if len(phone) < 10:
        return "Please enter a valid phone number (at least 10 digits).", False
    
    session.set_value('phone', phone)
    session.next_step()
    update_session(session)
    
    data = session.data
    
    return f"""*Confirm Your Appointment*

━━━━━━━━━━━━━━━━━━━━━
*Appointment Details:*
━━━━━━━━━━━━━━━━━━━━━
Patient: {data['patient_name']}
Doctor: {data['doctor_name']}
Specialty: {data['doctor_specialty']}
Date: {data['date']}
Time: {data['time']}
Phone: {phone}
━━━━━━━━━━━━━━━━━━━━━

Reply *YES* to confirm or *NO* to cancel.""", False


def _handle_appointment_confirm(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle final appointment confirmation."""
    response = user_input.lower().strip()
    
    if response in ['yes', 'y', 'confirm', 'ok']:
        data = session.data
        booking_id = _generate_booking_id('APT')
        
        saved = save_appointment(
            booking_id=booking_id,
            user_id=session.user_id,
            patient_name=data['patient_name'],
            department=data['doctor_specialty'],
            department_name=data['doctor_specialty'],
            doctor=data['doctor_name'],
            date=data['date'],
            time_slot=data['time'],
            clinic_id=clinic_id,
            phone=data.get('phone')
        )
        
        if not saved:
            return "Failed to save appointment. Please try again or call reception.", True
        
        delete_session(session.user_id)
        social = clinic.get('social_media', {})
        
        return f"""*Appointment Confirmed!*

Your booking reference: *{booking_id}*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Patient: {data['patient_name']}
Doctor: {data['doctor_name']} ({data['doctor_specialty']})
Date: {data['date']}
Time: {data['time']}
━━━━━━━━━━━━━━━━━━━━━

Location: {clinic['address']}
Contact: {clinic['phone']}

━━━━━━━━━━━━━━━━━━━━━
*Stay Connected:*
━━━━━━━━━━━━━━━━━━━━━
Website: {clinic.get('website', 'mallikahospitals.in')}
YouTube: {social.get('youtube', '')}
Instagram: {social.get('instagram', '')}
Facebook: {social.get('facebook', '')}

_Please arrive 15 minutes early._
Save your booking ID: *{booking_id}*
Need to cancel? Reply: *cancel {booking_id}*

Type *menu* for main menu.""", True
    
    elif response in ['no', 'n', 'cancel']:
        delete_session(session.user_id)
        return "Appointment cancelled. Type *menu* for main menu.", True
    
    return "Please reply *YES* to confirm or *NO* to cancel.", False


# ============================================================================
# DIAGNOSTICS FLOW
# ============================================================================

def start_diagnostics_flow(user_id: str, clinic_id: str = None) -> Tuple[str, bool]:
    """Start diagnostics booking flow."""
    existing = get_session(user_id)
    if existing:
        delete_session(user_id)
    
    session = create_session(user_id, 'diagnostics')
    tests = get_diagnostics_tests()
    
    # Format test menu as specified
    message = """*Book Diagnostic Test*

Please select a test:

1️⃣ ECG
2️⃣ 4D ECHO
3️⃣ TMT
4️⃣ Coronary Angiogram
5️⃣ MRI
6️⃣ CT Scan
7️⃣ Blood Investigation

Reply with the *number* of your choice.
Type *cancel* or *menu* to go back."""
    
    logger.info(f"Started diagnostics flow for user {user_id[:6]}***")
    return message, True


def process_diagnostics_input(user_id: str, user_input: str, clinic_id: str = None) -> Tuple[str, bool]:
    """Process user input during diagnostics flow."""
    session = get_session(user_id)
    if not session:
        return "No active session. Type *2* to book diagnostics.", True
    
    clinic = get_clinic_config(clinic_id)
    user_input = user_input.strip()
    
    if user_input.lower() in ['cancel', 'stop', 'exit', 'quit', 'menu']:
        delete_session(user_id)
        return "Booking cancelled. Type *menu* for main menu.", True
    
    step = session.step
    
    handlers = {
        'test': _handle_diagnostics_test,
        'patient_name': _handle_diagnostics_name,
        'date': _handle_diagnostics_date,
        'time': _handle_diagnostics_time,
        'phone': _handle_diagnostics_phone,
        'confirm': _handle_diagnostics_confirm
    }
    
    handler = handlers.get(step)
    if handler:
        return handler(session, user_input, clinic, clinic_id)
    
    delete_session(user_id)
    return "Something went wrong. Type *2* to start again.", True


def _handle_diagnostics_test(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle test selection."""
    try:
        tests = get_diagnostics_tests()
        choice = int(user_input)
        
        if 1 <= choice <= len(tests):
            test = tests[choice - 1]
            session.set_value('test_type', test['id'])
            session.set_value('test_name', test['name'])
            session.next_step()
            update_session(session)
            
            return f"""Selected: *{test['name']}*
_{test['description']}_

*Enter Patient Name:*
Please enter the full name of the patient.""", False
        else:
            return f"Please enter a number between 1 and {len(tests)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_diagnostics_name(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle patient name for diagnostics."""
    name = user_input.strip()
    
    if len(name) < 2:
        return "Please enter a valid name (at least 2 characters).", False
    
    session.set_value('patient_name', name)
    session.next_step()
    update_session(session)
    
    dates = _get_available_dates()
    date_lines = [f"*{i}* - {d}" for i, d in enumerate(dates, 1)]
    
    return f"""Patient: *{name}*

*Select Date:*

{chr(10).join(date_lines)}

Reply with the *number*.""", False


def _handle_diagnostics_date(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle date selection for diagnostics."""
    try:
        dates = _get_available_dates()
        choice = int(user_input)
        
        if 1 <= choice <= len(dates):
            session.set_value('date', dates[choice - 1])
            session.next_step()
            update_session(session)
            
            # Diagnostic time slots (fewer options)
            slots = ["08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM"]
            slot_lines = [f"*{i}* - {s}" for i, s in enumerate(slots, 1)]
            
            return f"""Selected: *{dates[choice - 1]}*

*Select Time:*

{chr(10).join(slot_lines)}

Reply with the *number*.""", False
        else:
            return f"Please enter a number between 1 and {len(dates)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_diagnostics_time(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle time selection for diagnostics."""
    try:
        slots = ["08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM"]
        choice = int(user_input)
        
        if 1 <= choice <= len(slots):
            session.set_value('time', slots[choice - 1])
            session.next_step()
            update_session(session)
            
            return f"""Selected: *{slots[choice - 1]}*

*Enter Phone Number:*
Please enter the contact phone number.""", False
        else:
            return f"Please enter a number between 1 and {len(slots)}.", False
    except ValueError:
        return "Please enter a valid number.", False


def _handle_diagnostics_phone(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle phone for diagnostics."""
    phone = user_input.strip().replace(' ', '').replace('-', '')
    
    if len(phone) < 10:
        return "Please enter a valid phone number (at least 10 digits).", False
    
    session.set_value('phone', phone)
    session.next_step()
    update_session(session)
    
    data = session.data
    
    return f"""*Confirm Diagnostic Booking*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Test: {data['test_name']}
Patient: {data['patient_name']}
Date: {data['date']}
Time: {data['time']}
Phone: {phone}
━━━━━━━━━━━━━━━━━━━━━

Reply *YES* to confirm or *NO* to cancel.""", False


def _handle_diagnostics_confirm(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle diagnostics confirmation."""
    response = user_input.lower().strip()
    
    if response in ['yes', 'y', 'confirm', 'ok']:
        data = session.data
        booking_id = _generate_booking_id('DGN')
        
        saved = save_diagnostic(
            booking_id=booking_id,
            user_id=session.user_id,
            patient_name=data['patient_name'],
            test_type=data['test_name'],
            date=data['date'],
            time_slot=data['time'],
            phone=data.get('phone')
        )
        
        if not saved:
            return "Failed to save booking. Please try again or call reception.", True
        
        delete_session(session.user_id)
        social = clinic.get('social_media', {})
        
        return f"""*Diagnostic Test Confirmed!*

Your booking reference: *{booking_id}*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Test: {data['test_name']}
Patient: {data['patient_name']}
Date: {data['date']}
Time: {data['time']}
━━━━━━━━━━━━━━━━━━━━━

Location: {clinic['address']}
Contact: {clinic['phone']}

━━━━━━━━━━━━━━━━━━━━━
*Instructions:*
━━━━━━━━━━━━━━━━━━━━━
- Please arrive 15 minutes early
- Bring any previous reports if available
- Follow fasting instructions if applicable

━━━━━━━━━━━━━━━━━━━━━
*Stay Connected:*
━━━━━━━━━━━━━━━━━━━━━
Website: {clinic.get('website', 'mallikahospitals.in')}
Instagram: {social.get('instagram', '')}

Save your booking ID: *{booking_id}*

Type *menu* for main menu.""", True
    
    elif response in ['no', 'n', 'cancel']:
        delete_session(session.user_id)
        return "Booking cancelled. Type *menu* for main menu.", True
    
    return "Please reply *YES* to confirm or *NO* to cancel.", False


# ============================================================================
# ADMISSION FLOW
# ============================================================================

def start_admission_flow(user_id: str, clinic_id: str = None) -> Tuple[str, bool]:
    """Start admission request flow."""
    existing = get_session(user_id)
    if existing:
        delete_session(user_id)
    
    session = create_session(user_id, 'admission')
    
    message = """*Hospital Admission*

Please select admission type:

1️⃣ Emergency Admission (Urgent/Critical)
2️⃣ Non-Emergency Admission (Planned)

Reply with the *number* of your choice.
Type *cancel* or *menu* to go back.

_For immediate emergencies, call: +91 98854 54128_"""
    
    logger.info(f"Started admission flow for user {user_id[:6]}***")
    return message, True


def process_admission_input(user_id: str, user_input: str, clinic_id: str = None) -> Tuple[str, bool]:
    """Process user input during admission flow."""
    session = get_session(user_id)
    if not session:
        return "No active session. Type *3* for admission.", True
    
    clinic = get_clinic_config(clinic_id)
    user_input = user_input.strip()
    
    if user_input.lower() in ['cancel', 'stop', 'exit', 'quit', 'menu']:
        delete_session(user_id)
        return "Request cancelled. Type *menu* for main menu.", True
    
    step = session.step
    
    handlers = {
        'admission_type': _handle_admission_type,
        'patient_name': _handle_admission_name,
        'age': _handle_admission_age,
        'sex': _handle_admission_sex,
        'confirm': _handle_admission_confirm
    }
    
    handler = handlers.get(step)
    if handler:
        return handler(session, user_input, clinic, clinic_id)
    
    delete_session(user_id)
    return "Something went wrong. Type *3* to start again.", True


def _handle_admission_type(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle admission type selection."""
    try:
        choice = int(user_input)
        
        if choice == 1:
            session.set_value('admission_type', 'Emergency')
            session.next_step()
            update_session(session)
            
            return """*Emergency Admission*

*Enter Patient Name:*
Please enter the full name of the patient.

_For critical emergencies, please call: +91 98854 54128_""", False
        
        elif choice == 2:
            session.set_value('admission_type', 'Non-Emergency')
            session.next_step()
            update_session(session)
            
            return """*Non-Emergency Admission*

*Enter Patient Name:*
Please enter the full name of the patient.

Or type *walkin* if patient will provide details at reception.""", False
        
        else:
            return "Please enter *1* for Emergency or *2* for Non-Emergency.", False
    
    except ValueError:
        return "Please enter *1* for Emergency or *2* for Non-Emergency.", False


def _handle_admission_name(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle patient name for admission."""
    name = user_input.strip()
    
    # Check for walkin option
    if name.lower() == 'walkin':
        session.set_value('patient_name', 'Walk-in Patient')
        session.set_value('is_walkin', True)
        session.step = 'confirm'  # Skip to confirm
        update_session(session)
        
        data = session.data
        return f"""*Confirm Walk-in Admission Request*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Type: {data['admission_type']}
Patient: Walk-in (Details at reception)
━━━━━━━━━━━━━━━━━━━━━

Reply *YES* to confirm or *NO* to cancel.""", False
    
    if len(name) < 2:
        return "Please enter a valid name (at least 2 characters).", False
    
    session.set_value('patient_name', name)
    session.next_step()
    update_session(session)
    
    return f"""Patient: *{name}*

*Enter Patient Age:*
Please enter the patient's age in years.""", False


def _handle_admission_age(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle age input for admission."""
    try:
        age = int(user_input.strip())
        if age < 0 or age > 150:
            return "Please enter a valid age.", False
        
        session.set_value('age', str(age))
        session.next_step()
        update_session(session)
        
        return f"""Age: *{age} years*

*Select Patient Gender:*

*1* - Male
*2* - Female
*3* - Other

Reply with the *number*.""", False
    
    except ValueError:
        return "Please enter a valid age number.", False


def _handle_admission_sex(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle gender selection for admission."""
    try:
        choice = int(user_input)
        gender_map = {1: 'Male', 2: 'Female', 3: 'Other'}
        
        if choice in gender_map:
            session.set_value('sex', gender_map[choice])
            session.next_step()
            update_session(session)
            
            data = session.data
            
            return f"""*Confirm Admission Request*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Type: {data['admission_type']}
Patient: {data['patient_name']}
Age: {data['age']} years
Gender: {data['sex']}
━━━━━━━━━━━━━━━━━━━━━

Reply *YES* to confirm or *NO* to cancel.""", False
        else:
            return "Please enter *1*, *2*, or *3*.", False
    
    except ValueError:
        return "Please enter a valid number.", False


def _handle_admission_confirm(session: BookingSession, user_input: str, clinic: dict, clinic_id: str) -> Tuple[str, bool]:
    """Handle admission confirmation."""
    response = user_input.lower().strip()
    
    if response in ['yes', 'y', 'confirm', 'ok']:
        data = session.data
        admission_id = _generate_booking_id('ADM')
        
        saved = save_admission(
            admission_id=admission_id,
            user_id=session.user_id,
            patient_name=data['patient_name'],
            age=data.get('age'),
            sex=data.get('sex'),
            admission_type=data['admission_type'],
            preferred_date=data.get('preferred_date'),
            phone=session.user_id,  # Auto-capture from WhatsApp
            is_walkin=data.get('is_walkin', False)
        )
        
        if not saved:
            return "Failed to save request. Please call reception: +91 98854 54128", True
        
        delete_session(session.user_id)
        
        if data['admission_type'] == 'Emergency':
            return f"""*Emergency Admission Request Received!*

Reference ID: *{admission_id}*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Patient: {data['patient_name']}
Age: {data.get('age', 'N/A')} years
Gender: {data.get('sex', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━

*URGENT: Please call immediately*
*Reception:* +91 98854 54128
*Emergency:* +91 96741 08108

Our team will contact you shortly.

Location: {clinic['address']}

Type *menu* for main menu.""", True
        else:
            return f"""*Admission Request Confirmed!*

Reference ID: *{admission_id}*

━━━━━━━━━━━━━━━━━━━━━
*Details:*
━━━━━━━━━━━━━━━━━━━━━
Type: {data['admission_type']}
Patient: {data['patient_name']}
Age: {data.get('age', 'N/A')} years
Gender: {data.get('sex', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━

Our team will contact you within 24 hours to discuss:
- Available rooms
- Admission date
- Required documents
- Estimated costs

Contact: {clinic['phone']}
Location: {clinic['address']}

Save your reference ID: *{admission_id}*

Type *menu* for main menu.""", True
    
    elif response in ['no', 'n', 'cancel']:
        delete_session(session.user_id)
        return "Request cancelled. Type *menu* for main menu.", True
    
    return "Please reply *YES* to confirm or *NO* to cancel.", False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _get_available_dates() -> list:
    """Get next 7 available dates (excluding Sunday)."""
    dates = []
    current = datetime.now() + timedelta(days=1)
    
    while len(dates) < 7:
        if current.weekday() != 6:  # Skip Sunday
            dates.append(current.strftime("%a, %d %b %Y"))
        current += timedelta(days=1)
    
    return dates


def _generate_booking_id(prefix: str = 'APT') -> str:
    """Generate unique booking ID with prefix."""
    timestamp = datetime.now().strftime("%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{timestamp}{random_part}"


def cancel_booking(user_id: str, booking_id: str = None) -> str:
    """Cancel a booking by ID."""
    if not booking_id:
        return """Please provide your booking ID.

Example: *cancel APT02031234*

Type *status* to check your bookings."""
    
    booking_id = booking_id.upper().strip()
    
    # Check appointment
    if booking_id.startswith('APT'):
        appointment = get_appointment(booking_id)
        if appointment:
            if appointment['status'] == 'cancelled':
                return f"Booking *{booking_id}* was already cancelled."
            if db_cancel(booking_id):
                return f"""*Booking Cancelled*

Booking *{booking_id}* has been cancelled.

If you need to book again, type *1* for appointment or *menu* for main menu."""
    
    # Check diagnostic
    elif booking_id.startswith('DGN'):
        diagnostic = get_diagnostic(booking_id)
        if diagnostic:
            return f"To cancel diagnostic booking *{booking_id}*, please call: +91 98854 54128"
    
    # Check admission
    elif booking_id.startswith('ADM'):
        admission = get_admission(booking_id)
        if admission:
            return f"To cancel admission request *{booking_id}*, please call: +91 98854 54128"
    
    return f"Booking *{booking_id}* not found. Please check the ID and try again."


def check_status(user_id: str, booking_id: str = None) -> str:
    """Check booking status by ID."""
    if not booking_id:
        return """Please provide your booking ID.

Example: *status APT02031234*

Type *menu* to return to main menu."""
    
    booking_id = booking_id.upper().strip()
    
    # Check appointment
    if booking_id.startswith('APT'):
        appointment = get_appointment(booking_id)
        if appointment:
            status_emoji = "✅" if appointment['status'] == 'confirmed' else "❌"
            return f"""{status_emoji} *Appointment Status: {appointment['status'].upper()}*

━━━━━━━━━━━━━━━━━━━━━
Booking ID: {booking_id}
Patient: {appointment['patient_name']}
Doctor: {appointment['doctor']}
Date: {appointment['date']}
Time: {appointment['time']}
━━━━━━━━━━━━━━━━━━━━━

Type *menu* for main menu."""
    
    # Check diagnostic
    elif booking_id.startswith('DGN'):
        diagnostic = get_diagnostic(booking_id)
        if diagnostic:
            status_emoji = "✅" if diagnostic['status'] == 'confirmed' else "❌"
            return f"""{status_emoji} *Diagnostic Status: {diagnostic['status'].upper()}*

━━━━━━━━━━━━━━━━━━━━━
Booking ID: {booking_id}
Test: {diagnostic['test_type']}
Patient: {diagnostic['patient_name']}
Date: {diagnostic['date']}
Time: {diagnostic['time']}
━━━━━━━━━━━━━━━━━━━━━

Type *menu* for main menu."""
    
    # Check admission
    elif booking_id.startswith('ADM'):
        admission = get_admission(booking_id)
        if admission:
            status_emoji = "⏳" if admission['status'] == 'pending' else "✅"
            return f"""{status_emoji} *Admission Status: {admission['status'].upper()}*

━━━━━━━━━━━━━━━━━━━━━
Reference ID: {booking_id}
Type: {admission['admission_type']}
Patient: {admission['patient_name']}
━━━━━━━━━━━━━━━━━━━━━

For updates, call: +91 98854 54128

Type *menu* for main menu."""
    
    return f"Booking *{booking_id}* not found. Please check the ID and try again."
