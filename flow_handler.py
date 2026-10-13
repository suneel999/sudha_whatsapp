"""
WhatsApp Flow Handler - Mallika Hospitals Appointment Booking

Handles WhatsApp Flows for appointment booking:
1. Doctor Selection (with specialties)
2. Date and Time Selection  
3. Patient Details
4. Confirmation and Booking

CRITICAL FIXES APPLIED:
1. Flow uses navigate action but wasn't sending initial data
2. data_exchange responses must return ALL screen fields
3. Every response MUST have "screen" and "data" keys
4. Encryption errors must return HTTP 421
"""

import os
import json
import logging
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from config import get_clinic_config
from database import (
    save_appointment, save_flow_data as db_save_flow, 
    get_flow_data as db_get_flow, clear_flow_data as db_clear_flow
)
from booking_engine import _generate_booking_id
from whatsapp_client import send_text_message

logger = logging.getLogger(__name__)

def get_flow_data(token: str) -> Dict[str, Any]:
    """Retrieve stored flow data."""
    return db_get_flow(token)


def clear_flow_data(token: str):
    """Clear stored flow data."""
    db_clear_flow(token)

# =============================================================================
# ENCRYPTION SETUP
# =============================================================================

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not installed. Run: pip install cryptography")


# =============================================================================
# DOCTORS LIST
# =============================================================================

DOCTORS = [
    {"id": "dr_mahesh", "name": "Dr. Mahesh Babu", "specialty": "Cardiology"},
    {"id": "dr_mounika", "name": "Dr. Mounika Reddy", "specialty": "Neurology"},
    {"id": "dr_rahul", "name": "Dr. Rahul", "specialty": "Orthopedics"}
]


def get_doctors_list() -> list:
    """Get doctors as Flow data source."""
    return [
        {"id": doc["id"], "title": f"{doc['name']} ({doc['specialty']})"}
        for doc in DOCTORS
    ]


def get_doctor_by_id(doctor_id: str) -> dict:
    """Get doctor details by ID."""
    for doc in DOCTORS:
        if doc["id"] == doctor_id:
            return doc
    return {"id": doctor_id, "name": doctor_id, "specialty": "Specialist"}


# =============================================================================
# ENCRYPTION/DECRYPTION FUNCTIONS
# =============================================================================

def load_private_key():
    """Load private key from file for decryption."""
    key_path = os.getenv('PRIVATE_KEY_PATH', 'private_key.pem')
    
    if not os.path.exists(key_path):
        logger.error(f"CRITICAL: Private key not found at {key_path}")
        return None
    
    try:
        with open(key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        return private_key
    except Exception as e:
        logger.error(f"Failed to load private key: {e}")
        return None


def decrypt_request(encrypted_data: dict, private_key) -> Tuple[Optional[dict], Optional[bytes], Optional[bytes]]:
    """
    Decrypt incoming Flow request from Meta.
    
    Returns:
        Tuple of (decrypted_data, aes_key, iv) or (None, None, None) on failure
    """
    if not CRYPTO_AVAILABLE:
        logger.error("Cryptography library not available")
        return None, None, None
    
    try:
        encrypted_aes_key = base64.b64decode(encrypted_data['encrypted_aes_key'])
        encrypted_flow_data = base64.b64decode(encrypted_data['encrypted_flow_data'])
        initial_vector = base64.b64decode(encrypted_data['initial_vector'])
        
        # Decrypt AES key using RSA private key with OAEP padding
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt flow data using AES-GCM
        aesgcm = AESGCM(aes_key)
        decrypted_data = aesgcm.decrypt(initial_vector, encrypted_flow_data, None)
        
        # Parse JSON
        flow_data = json.loads(decrypted_data.decode('utf-8'))
        
        logger.info(f"Decrypted flow request: action={flow_data.get('action')}, screen={flow_data.get('screen')}")
        
        return flow_data, aes_key, initial_vector
        
    except Exception as e:
        logger.error(f"Decryption failed: {e}", exc_info=True)
        return None, None, None


def encrypt_response(response_data: dict, aes_key: bytes, iv: bytes) -> str:
    """
    Encrypt response data for Meta.
    
    CRITICAL: Meta requires the IV to be flipped for the response.
    """
    if not CRYPTO_AVAILABLE:
        logger.error("Cryptography library not available")
        return ""
    
    try:
        # IMPORTANT: Flip the IV for response (Meta requirement)
        flipped_iv = bytes(~b & 0xFF for b in iv)
        
        # Encrypt response using AES-GCM
        aesgcm = AESGCM(aes_key)
        response_json = json.dumps(response_data).encode('utf-8')
        encrypted_response = aesgcm.encrypt(flipped_iv, response_json, None)
        
        return base64.b64encode(encrypted_response).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Encryption failed: {e}", exc_info=True)
        return ""


# =============================================================================
# DATA PROVIDERS
# =============================================================================

def get_available_dates(doctor_id: Optional[str] = None) -> list:
    """Get available dates for the next 3 months. Dr. Mahesh: no Thu/Sun; others: no Sun. Smooth list for Flow dropdown."""
    dates = []
    # Start from tomorrow; end at 3 months (90 days) for a smooth range
    current = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end = current + timedelta(days=90)
    is_dr_mahesh = doctor_id and (doctor_id.lower() == "dr_mahesh" or "mahesh" in doctor_id.lower())

    while current < end and len(dates) < 45:  # cap at 45 so ~6–7 weeks of selectable dates
        wd = current.weekday()  # 0 Mon .. 6 Sun
        skip = False
        if wd == 6:
            skip = True  # Sunday: all doctors
        elif is_dr_mahesh and wd == 3:
            skip = True  # Thursday: Dr. Mahesh only
        if not skip:
            dates.append({
                "id": current.strftime("%Y-%m-%d"),
                "title": current.strftime("%a, %d %b %Y")
            })
        current += timedelta(days=1)

    return dates


def get_time_slots(clinic: dict) -> list:
    """Get time slots."""
    slots = clinic.get("time_slots", [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM"
    ])
    return [{"id": slot, "title": slot} for slot in slots]


# =============================================================================
# SAFE FALLBACK RESPONSE
# =============================================================================

def get_safe_fallback_response(clinic: dict) -> Dict[str, Any]:
    """Returns a safe fallback response that will never cause white screen."""
    return {
        "screen": "APPOINTMENT",
        "data": {
            "doctors": get_doctors_list(),
            "dates": [{"id": "_placeholder", "title": "Select doctor first"}],
            "is_dates_enabled": False,
            "time_slots": [{"id": "_placeholder", "title": "Select date first"}],
            "is_time_enabled": False
        }
    }


# =============================================================================
# MAIN FLOW REQUEST HANDLER
# =============================================================================

def handle_flow_request(request_data: dict, clinic_id: str = None, is_encrypted: bool = False) -> Dict[str, Any]:
    """
    Main dispatcher for Flow requests.
    
    CRITICAL: This function MUST ALWAYS return a valid response with:
    - "screen": string (screen ID to display/update)
    - "data": dict (all data fields required by that screen)
    """
    clinic = get_clinic_config(clinic_id)
    
    action = request_data.get("action", "")
    screen = request_data.get("screen", "")
    data = request_data.get("data", {}) or {}
    payload = request_data.get("payload", {}) or {}
    # flow_token can be at top level or inside data/payload (Meta API variation)
    flow_token = (
        request_data.get("flow_token")
        or (data if isinstance(data, dict) else {}).get("flow_token")
        or (payload if isinstance(payload, dict) else {}).get("flow_token")
        or ""
    )
    if isinstance(flow_token, dict):
        flow_token = ""
    flow_token = str(flow_token).strip() if flow_token else ""
    
    logger.info("=" * 60)
    logger.info(f"FLOW REQUEST - Action: {action}, Screen: {screen}")
    logger.info(f"Data: {json.dumps(data, indent=2)}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")
    logger.info("=" * 60)
    
    try:
        response = None
        # PING - Health Check
        if action.lower() == "ping":
            logger.info("FLOW REQUEST: Action is PING, returning active status")
            response = {"data": {"status": "active"}}
        
        # INIT - Flow Opened
        elif action.upper() == "INIT":
            logger.info("FLOW REQUEST: Action is INIT")
            response = build_appointment_screen_initial(clinic)
        
        # DATA_EXCHANGE - User Selection
        elif action == "data_exchange":
            logger.info(f"FLOW REQUEST: Action is data_exchange, screen={screen}")
            response = handle_data_exchange(screen, data, payload, clinic, flow_token)
        
        # COMPLETE - Flow Submitted
        elif action.upper() == "COMPLETE":
            logger.info("FLOW REQUEST: Action is COMPLETE")
            response = handle_complete(data, payload, flow_token, clinic, clinic_id)
        
        if response:
            # Standard Flow Header per Meta Docs
            response["version"] = "3.0"
            logger.info("MANDATORY_LOG: Returning valid Flow response: screen=%s", response.get("screen"))
            return response
        
        # Unknown action
        logger.warning(f"Unknown action: {action}")
        fallback = get_safe_fallback_response(clinic)
        fallback["version"] = "3.0"
        return fallback
        
        # Unknown action
        logger.warning(f"Unknown action: {action}")
        return get_safe_fallback_response(clinic)
        
    except Exception as e:
        logger.error(f"Exception in handle_flow_request: {e}", exc_info=True)
        return get_safe_fallback_response(clinic)


# =============================================================================
# DATA EXCHANGE HANDLER
# =============================================================================

def handle_data_exchange(screen: str, data: dict, payload: dict, clinic: dict, flow_token: str = None) -> Dict[str, Any]:
    """
    Handle data_exchange action.
    
    CRITICAL: Always merge payload + data to preserve all selections.
    payload = new user input
    data = previously accumulated data
    merged = complete state
    """
    
    trigger = payload.get("trigger", "")
    
    # CRITICAL FIX: Always merge payload with data to preserve state
    merged = {**data, **payload}
    # Some clients send form values nested under "form"
    form = payload.get("form") or data.get("form") or {}
    if form:
        merged = {**merged, **form}
    
    logger.info(f"DATA_EXCHANGE - Screen: {screen}, Trigger: {trigger}")
    logger.info(f"  Merged data: {json.dumps(merged, indent=2)}")
    
    try:
        # APPOINTMENT SCREEN - Doctor/Date/Time Selection
        if screen == "APPOINTMENT":
            doctor_id = merged.get("doctor") or payload.get("doctor") or form.get("doctor")
            date_id = merged.get("appointment_date") or payload.get("appointment_date") or form.get("appointment_date")
            time_id = merged.get("time_slot") or payload.get("time_slot") or form.get("time_slot")
            # Normalize: strip and treat empty string as unset
            doctor_id = (doctor_id or "").strip() or None
            date_id = (date_id or "").strip() or None
            time_id = (time_id or "").strip() or None
            
            logger.info(f"  Doctor: {doctor_id}, Date: {date_id}, Time: {time_id}")
            
            # STORE DATA PERSISTENTLY
            if flow_token:
                db_save_flow(flow_token, merged)
                logger.info("MANDATORY_LOG: Flow data stored with token: %s", flow_token)
            
            return build_appointment_screen_response(clinic, doctor_id, date_id, time_id, merged)
        
        # DETAILS SCREEN - Patient Details Submitted
        if screen == "DETAILS":
            # STORE DATA PERSISTENTLY
            if flow_token:
                db_save_flow(flow_token, merged)
                logger.info("MANDATORY_LOG: Flow data stored with token: %s", flow_token)
            return build_summary_screen_response(merged, clinic)
        
        # SUMMARY SCREEN - Treat as completion
        if screen == "SUMMARY":
            logger.info("SUMMARY data_exchange -> treating as COMPLETE")
            return handle_summary_complete(data, payload, flow_token, clinic)
        
        # Unknown screen - use merged data to preserve state
        logger.warning(f"Unknown screen: {screen}, returning safe response with merged data")
        return get_safe_fallback_response(clinic)
        
    except Exception as e:
        logger.error(f"Exception in handle_data_exchange: {e}", exc_info=True)
        return get_safe_fallback_response(clinic)


# =============================================================================
# SCREEN RESPONSE BUILDERS
# =============================================================================

def build_appointment_screen_initial(clinic: dict) -> Dict[str, Any]:
    """Build initial response for APPOINTMENT screen."""
    return {
        "screen": "APPOINTMENT",
        "data": {
            "doctors": get_doctors_list(),
            "dates": [{"id": "_placeholder", "title": "Select doctor first"}],
            "is_dates_enabled": False,
            "time_slots": [{"id": "_placeholder", "title": "Select date first"}],
            "is_time_enabled": False
        }
    }


def build_appointment_screen_response(
    clinic: dict,
    doctor_id: Optional[str],
    date_id: Optional[str],
    time_id: Optional[str] = None,
    merged_data: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Build response for APPOINTMENT screen with cascading dropdowns.
    
    CRITICAL: Response must preserve all previously selected values
    to prevent losing user selections.
    """
    
    doctors = get_doctors_list()
    dates = []
    is_dates_enabled = False
    times = []
    is_time_enabled = False
    
    # If doctor selected -> enable dates
    if doctor_id and doctor_id != "_placeholder":
        dates = get_available_dates(doctor_id)
        if not dates:
            # Fallback: ensure we always have dates when doctor is selected (e.g. old DB / edge case)
            dates = get_available_dates(None)
        is_dates_enabled = True
        logger.info(f"  -> Doctor selected ({doctor_id}), enabling dates ({len(dates)} options)")
    
    # If date selected -> enable times
    if doctor_id and date_id and doctor_id != "_placeholder" and date_id != "_placeholder":
        times = get_time_slots(clinic)
        is_time_enabled = True
        logger.info(f"  -> Date selected ({date_id}), enabling times ({len(times)} options)")
    
    response_data = {
        "doctors": doctors,
        "dates": dates if dates else [{"id": "_placeholder", "title": "Select doctor first"}],
        "is_dates_enabled": is_dates_enabled,
        "time_slots": times if times else [{"id": "_placeholder", "title": "Select date first"}],
        "is_time_enabled": is_time_enabled
    }
    
    # CRITICAL: Include previously selected values to preserve state
    # This prevents the Flow from losing the user's selections
    if doctor_id and doctor_id != "_placeholder":
        response_data["doctor"] = doctor_id
    if date_id and date_id != "_placeholder":
        response_data["appointment_date"] = date_id
    if time_id and time_id != "_placeholder":
        response_data["time_slot"] = time_id
    
    # Include any other merged data values needed for the next screen
    if merged_data:
        for key in ["patient_name", "phone", "patient_identifier"]:
            if merged_data.get(key):
                response_data[key] = merged_data[key]
    
    return {
        "screen": "APPOINTMENT",
        "data": response_data
    }


def build_summary_screen_response(data: dict, clinic: dict) -> Dict[str, Any]:
    """Build response for SUMMARY screen."""
    
    doctor_id = data.get("doctor", "")
    date_str = data.get("appointment_date", "")
    time_str = data.get("time_slot", "")
    patient_name = data.get("patient_name", "")
    phone = data.get("phone", "")
    patient_identifier = (data.get("patient_identifier") or "").strip()
    
    # Get doctor details
    doctor = get_doctor_by_id(doctor_id)
    doctor_name = f"{doctor['name']} ({doctor['specialty']})"
    
    # Format date for display
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%a, %d %b %Y")
    except:
        date_display = date_str
    
    summary_text = f"Doctor: {doctor_name}\nDate: {date_display}\nTime: {time_str}"
    patient_text = f"Patient: {patient_name}\nPhone: {phone}"
    if patient_identifier:
        patient_text += f"\nPatient ID: {patient_identifier}"
    
    return {
        "screen": "SUMMARY",
        "data": {
            "summary_text": summary_text,
            "patient_text": patient_text,
            "doctor": doctor_id,
            "doctor_name": doctor_name,
            "appointment_date": date_str,
            "time_slot": time_str,
            "patient_name": patient_name,
            "phone": phone,
            "patient_identifier": patient_identifier
        }
    }


# =============================================================================
# COMPLETE HANDLER
# =============================================================================


def format_confirmation_message(booking_data: dict, clinic: dict) -> str:
    """Format appointment confirmation message sent after Flow completion."""
    booking_id = booking_data.get("booking_id", "N/A")
    doctor_name = booking_data.get("doctor_name", "N/A")
    date_str = booking_data.get("date", "N/A")
    time_str = booking_data.get("time", "N/A")
    patient_name = booking_data.get("patient_name", "")
    phone = booking_data.get("phone", "")
    patient_identifier = (booking_data.get("patient_identifier") or "").strip()

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%d %b %Y")
    except Exception:
        date_display = date_str

    patient_id_line = f"\nPatient ID: {patient_identifier}" if patient_identifier else ""

    return f"""Appointment Confirmed

Booking ID: {booking_id}
Doctor: {doctor_name}
Date: {date_display}
Time: {time_str}
Patient: {patient_name}
Phone: {phone}{patient_id_line}

{clinic['name']}
{clinic.get('address', '')}

Contact: {clinic['phone']}
Website: {clinic.get('website', 'mallikahospitals.in')}

Please arrive 15 minutes before your appointment.
Need to cancel? Reply: cancel {booking_id}"""


def handle_complete(data: dict, payload: dict, flow_token: str, clinic: dict, clinic_id: str) -> Dict[str, Any]:
    """
    Handle COMPLETE action - Redundancy check.
    If Meta sends data here, we use it. If not, we rely on stored data in the webhook.
    """
    # Merge and update store just in case data is sent here
    merged_data = {**data, **payload}
    form = payload.get("form") or data.get("form") or {}
    merged_data = {**merged_data, **form}
    
    if flow_token and merged_data:
        # Merge handled inside db_save_flow
        db_save_flow(flow_token, merged_data)
        logger.info("MANDATORY_LOG: Flow data updated in COMPLETE for token: %s", flow_token)

    # Note: process_flow_booking will be called by the webhook handler to ensure
    # the exact same logic runs whether data comes here or via nfm_reply.
    
    return {
        "screen": "SUMMARY",
        "data": {
            "extension_message_response": {
                "params": {
                    "status": "success",
                    "flow_token": flow_token
                }
            }
        }
    }


def process_flow_booking(flow_token: str, phone_number_id: str, user_wa_id: str = None) -> bool:
    """
    Finalize the booking process - SINGLE SOURCE OF TRUTH.
    Should be called from the Webhook handler when __FLOW_COMPLETED__ or nfm_reply is received.
    """
    if not flow_token:
        logger.error("MANDATORY_LOG: Cannot process booking without flow_token")
        return False

    # Retrieve stored data
    data = get_flow_data(flow_token)
    if not data:
        logger.error("MANDATORY_LOG: No stored flow data found for token: %s", flow_token)
        return False

    clinic = get_clinic_config(phone_number_id)
    
    # Extract details
    doctor_id = (data.get("doctor") or "").strip()
    date_str = (data.get("appointment_date") or "").strip()
    time_slot = (data.get("time_slot") or "").strip()
    patient_name = (data.get("patient_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    patient_identifier = (data.get("patient_identifier") or "").strip()
    
    logger.info("MANDATORY_LOG: Processing booking. Data: %s", json.dumps(data))
    
    if not doctor_id or not date_str or not time_slot:
        logger.error("MANDATORY_LOG: Missing required fields in stored data: doctor=%r, date=%r, time=%r. Full data: %s", 
                     doctor_id, date_str, time_slot, json.dumps(data))
        return False
    
    # Generate a NEW booking ID
    booking_id = _generate_booking_id('APT')
    
    # Get doctor name
    doctor = get_doctor_by_id(doctor_id)
    doctor_name = f"{doctor['name']} ({doctor['specialty']})"
    
    # Determine user identity. user_wa_id is the person who messaged us.
    # user_id is the primary key for the database record.
    # recipient_wa_id is where we send the confirmation.
    
    recipient_wa_id = user_wa_id or (flow_token.split('_')[0] if flow_token and '_' in flow_token else None)
    
    if not recipient_wa_id:
        # Fallback to phone from form if absolutely necessary, but log it
        recipient_wa_id = phone or "unknown"
        logger.warning("MANDATORY_LOG: No user_wa_id or token-extracted ID. Using phone from form: %s", recipient_wa_id)

    # In database, user_id should be the person who booked
    db_user_id = recipient_wa_id

    # Save appointment to database
    try:
        saved = save_appointment(
            booking_id=booking_id,
            user_id=db_user_id,
            patient_name=patient_name or "Patient",
            department=doctor['specialty'],
            department_name=doctor['specialty'],
            doctor=doctor_name,
            date=date_str,
            time_slot=time_slot,
            clinic_id=phone_number_id or 'default',
            phone=phone, # Store typed phone in DB
            source='whatsapp',
            patient_identifier=patient_identifier or None
        )
        
        if not saved:
            logger.error("MANDATORY_LOG: DB Insert Failed for Booking ID: %s", booking_id)
            return False

        logger.info("MANDATORY_LOG: Booking created with ID: %s", booking_id)

    except Exception as e:
        logger.error("MANDATORY_LOG: Exception during DB Insert: %s", str(e), exc_info=True)
        return False
    
    # Send confirmation message
    booking_record = {
        "booking_id": booking_id,
        "doctor_name": doctor_name,
        "date": date_str,
        "time": time_slot,
        "patient_name": patient_name,
        "phone": phone,
        "patient_identifier": patient_identifier
    }
    
    confirmation_msg = format_confirmation_message(booking_record, clinic)
    
    phone_number_id = phone_number_id or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    if phone_number_id and recipient_wa_id and recipient_wa_id != "unknown":
        from whatsapp_client import send_text_message
        # CRITICAL: Send to recipient_wa_id (the person who booked), NOT the phone from form
        send_text_message(recipient_wa_id, confirmation_msg, phone_number_id)
        logger.info("MANDATORY_LOG: Confirmation sent to %s", recipient_wa_id)
        return True
    else:
        logger.warning("MANDATORY_LOG: Skipping message send - missing phone or phone_number_id.")
        return True # DB was saved at least


def handle_summary_complete(data: dict, payload: dict, flow_token: str, clinic: dict) -> Dict[str, Any]:
    """Redirect to main handle_complete to ensure single source of truth."""
    return handle_complete(data, payload, flow_token, clinic, 'default')


# LEGACY helper removed - centralized in handle_complete


# =============================================================================
# ENCRYPTED FLOW REQUEST HANDLER
# =============================================================================

def handle_encrypted_flow_request(encrypted_data: dict, clinic_id: str = None) -> str:
    """
    Handle encrypted Flow request from Meta.
    
    Returns:
        Base64 encoded encrypted response, or empty string on failure
    """
    logger.info("Processing encrypted flow request...")
    
    private_key = load_private_key()
    if not private_key:
        logger.error("CRITICAL: Private key not available")
        return ""
    
    flow_data, aes_key, iv = decrypt_request(encrypted_data, private_key)
    
    if not flow_data:
        logger.error("MANDATORY_LOG: Flow decryption FAILED - check key/signature")
        return ""
    
    logger.info("MANDATORY_LOG: Flow decryption SUCCESS. Action: %s", flow_data.get("action"))
    response_data = handle_flow_request(flow_data, clinic_id, is_encrypted=True)
    
    logger.info(f"MANDATORY_LOG: Raw Flow response created (ready to encrypt)")
    
    encrypted_response = encrypt_response(response_data, aes_key, iv)
    
    if not encrypted_response:
        logger.error("MANDATORY_LOG: Response encryption FAILED")
        return ""
    
    logger.info("MANDATORY_LOG: Encrypted response sent to Meta")
    return encrypted_response


# =============================================================================
# SEND FLOW MESSAGE
# =============================================================================

def send_flow_message(to: str, flow_id: str, phone_number_id: str = None, flow_token: str = None) -> bool:
    """
    Send a Flow message to trigger appointment booking.
    """
    import requests
    
    phone_number_id = phone_number_id or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    token = os.getenv('WHATSAPP_TOKEN')
    
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Use provided token or generate a unique one
    if not flow_token:
        flow_token = f"{to}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": "Book Appointment"
            },
            "body": {
                "text": "Schedule your appointment with our specialists.\n\nTap the button below to get started."
            },
            "footer": {
                "text": "Mallika Hospitals"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_id": flow_id,
                    "flow_message_version": "3",
                    "flow_token": flow_token,
                    "flow_cta": "Book Now",
                    "flow_action": "data_exchange"
                }
            }
        }
    }
    
    try:
        logger.info(f"Sending Flow to {to[:6]}***")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Flow message sent successfully")
            return True
        else:
            logger.error(f"Flow send error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Flow send exception: {str(e)}")
        return False


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def verify_flow_signature(payload: bytes, signature: str) -> bool:
    """Verify the Flow request signature from Meta."""
    app_secret = os.getenv('APP_SECRET', '')
    if not app_secret:
        logger.warning("APP_SECRET not configured, skipping signature verification")
        return True
    
    expected_signature = hmac.new(
        app_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, f"sha256={expected_signature}")

