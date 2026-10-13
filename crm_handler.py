"""
CRM Handler - Production Ready
Manages patient profiles and interaction history for WhatsApp chatbot.
Provides unified patient management across all booking types.
"""

import logging
from typing import Optional, Dict, Any, List
from database import (
    get_patient, get_patient_by_phone, onboard_patient, log_interaction, 
    get_patient_history, get_chat_history, increment_booking_count,
    get_user_appointments, get_user_diagnostics, get_user_admissions,
    get_all_patients, get_dashboard_stats, get_recent_bookings,
    update_patient_name
)

logger = logging.getLogger(__name__)


def process_crm_message(
    external_id: str, 
    platform: str = 'whatsapp', 
    message: str = '',
    direction: str = 'inbound',
    message_type: str = 'text',
    payload: str = None
) -> int:
    """
    Onboard patient and log interaction.
    
    Args:
        external_id: WhatsApp phone number or user ID
        platform: Platform (whatsapp only for now)
        message: Message content
        direction: 'inbound' or 'outbound'
        message_type: 'text', 'button', 'list', 'flow' etc.
        payload: Button payload ID if applicable
    
    Returns:
        patient_id (int)
    """
    # 1. Onboard / Update patient profile
    patient_id = onboard_patient(external_id, platform)
    
    # 2. Log message to timeline
    log_interaction(
        patient_id=patient_id,
        direction=direction,
        platform=platform,
        message=message,
        user_id=external_id,
        message_type=message_type,
        payload=payload
    )
    
    logger.debug(f"CRM: Logged {direction} message for patient {patient_id}")
    return patient_id


def get_crm_context(external_id: str, platform: str = 'whatsapp') -> str:
    """
    Generate a summary of the patient's history for AI context.
    Safe - no sensitive medical data included.
    """
    patient = get_patient(external_id, platform)
    if not patient:
        return "Patient: New visitor."
    
    name = patient.get('name') or "Guest"
    total_appts = patient.get('total_appointments', 0)
    total_diag = patient.get('total_diagnostics', 0)
    total_adm = patient.get('total_admissions', 0)
    total_bookings = total_appts + total_diag + total_adm
    
    # Determine loyalty tier
    if total_bookings > 10:
        loyalty = "VIP Patient"
    elif total_bookings > 5:
        loyalty = "Regular Patient"
    elif total_bookings > 0:
        loyalty = "Returning Patient"
    else:
        loyalty = "New Patient"
    
    # Get recent appointments
    appointments = get_user_appointments(external_id, limit=2)
    recent_appts = []
    for appt in appointments:
        appt_date = appt.get('date', 'N/A')
        appt_time = appt.get('time', '')
        doctor = appt.get('doctor', 'N/A')
        recent_appts.append(f"{appt_date} - {doctor}")
    
    appt_str = ", ".join(recent_appts) if recent_appts else "No previous appointments."
    
    context = f"""[CRM CONTEXT]
- Patient Name: {name}
- Loyalty Status: {loyalty}
- Total Appointments: {total_appts}
- Total Diagnostics: {total_diag}
- Recent Visits: {appt_str}
"""
    return context


def get_patient_profile(external_id: str) -> Optional[Dict]:
    """
    Get complete patient profile with all bookings.
    Used for CRM dashboard.
    """
    patient = get_patient(external_id, 'whatsapp')
    if not patient:
        # Try by phone
        patient = get_patient_by_phone(external_id)
    
    if not patient:
        return None
    
    # Add booking history
    profile = dict(patient)
    profile['appointments'] = get_user_appointments(external_id, limit=10)
    profile['diagnostics'] = get_user_diagnostics(external_id, limit=10)
    profile['admissions'] = get_user_admissions(external_id, limit=10)
    profile['chat_history'] = get_chat_history(external_id, limit=50)
    
    return profile


def update_patient_profile(external_id: str, name: str = None):
    """Update patient name from booking or interaction."""
    if name:
        update_patient_name(external_id, name, 'whatsapp')


def handle_booking_confirmed(external_id: str, booking_type: str = 'appointment'):
    """
    Callback when a booking is confirmed.
    Updates CRM statistics.
    """
    patient = get_patient(external_id, 'whatsapp')
    if patient:
        increment_booking_count(patient['id'])
        logger.info(f"CRM: Booking count updated for patient {patient['id']}")


# ============================================================================
# CRM DASHBOARD FUNCTIONS
# ============================================================================

def get_crm_dashboard() -> Dict[str, Any]:
    """
    Get comprehensive CRM dashboard data.
    """
    stats = get_dashboard_stats()
    recent = get_recent_bookings(limit=20)
    patients = get_all_patients(limit=50)
    
    return {
        'stats': stats,
        'recent_bookings': recent,
        'patients': patients
    }


def get_patient_list(search: str = None, limit: int = 50) -> List[Dict]:
    """
    Get list of patients for CRM view.
    Optional search by name or phone.
    """
    patients = get_all_patients(limit=limit)
    
    if search:
        search_lower = search.lower()
        patients = [
            p for p in patients 
            if (p.get('name') and search_lower in p['name'].lower()) or
               (p.get('phone') and search in p['phone']) or
               (p.get('external_id') and search in p['external_id'])
        ]
    
    return patients


def get_conversation_for_patient(external_id: str) -> List[Dict]:
    """
    Get chat conversation history for a patient.
    Used for CRM chatbox view.
    """
    return get_chat_history(external_id, limit=100)


def log_outbound_message(external_id: str, message: str, message_type: str = 'text'):
    """
    Log outbound message sent to patient.
    """
    process_crm_message(
        external_id=external_id,
        platform='whatsapp',
        message=message,
        direction='outbound',
        message_type=message_type
    )