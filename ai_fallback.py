"""
AI Fallback Layer
Uses Gemini 1.5 Flash ONLY for general questions.
Strict constraints - NO medical advice, NO appointments, NO personal data.
"""

import os
import logging
from typing import Optional
import google.generativeai as genai
from data_safety import sanitize_for_ai, contains_medical_query
from config import get_clinic_config
from database import log_ai_interaction

logger = logging.getLogger(__name__)

# Initialize Gemini
_api_key = os.getenv('GEMINI_API_KEY', '')
if _api_key:
    genai.configure(api_key=_api_key)

# Generation config - slightly higher temperature for better personality
GENERATION_CONFIG = {
    'temperature': 0.3,          # Natural but controlled
    'top_p': 0.8,
    'top_k': 40,
    'max_output_tokens': 200,    # Allow a bit more space for buttons
}

# Request timeout in seconds
REQUEST_TIMEOUT = 10

# Fallback message - used when AI cannot/should not answer
FALLBACK_MESSAGE = """I don't have information about that.

📞 *Contact Reception:* +91 98854 54128

Type *help* to see what I can assist you with."""

# Topics AI must NEVER handle
BLOCKED_TOPICS = {
    'medical': ['diagnosis', 'treatment', 'prescription', 'medicine', 'dosage', 
                'symptom', 'pain', 'disease', 'cure', 'medication', 'drug',
                'should i take', 'what medicine', 'is it serious', 'am i sick',
                'side effect', 'allergic', 'fever', 'cough', 'headache'],
    'booking': ['book', 'appointment', 'schedule', 'cancel', 'reschedule',
                'confirm', 'reservation', 'slot', 'available'],
    'personal': ['my name', 'my phone', 'my address', 'my email', 'my number',
                 'patient id', 'medical record', 'health record']
}


def _build_system_prompt(clinic_context: str, crm_context: str = "") -> str:
    """
    Build strict system prompt with explicit restrictions.
    Includes CRM data for personalization if available.
    """
    simple_fallback = "Please contact Sudha Hospital reception for this information."

    return f"""You are the helpful and warm assistant for Sudha Hospital.
Your goal is to provide accurate hospital info AND guide the patient to the next step using interactive buttons.

=== PATIENT CRM CONTEXT ===
{crm_context}
(Use this to greet returning patients or acknowledge their history, but NEVER give medical results)

=== STRICT RULES (MUST FOLLOW) ===

1. ONLY answer if the information is EXPLICITLY stated in HOSPITAL INFORMATION below.
2. If information is NOT available, respond: "{simple_fallback}"
3. NEVER give medical advice, diagnosis, treatment suggestions, or medication information.
4. NEVER confirm, book, cancel, or modify appointments directly in text.
5. NEVER invent or assume information not in the context.
6. Keep responses under 80 words.
7. Be warm, professional, and empathetic.

=== INTERACTIVE BUTTONS ===
You MUST suggest NEXT STEPS using this format at the end of your message: 
[[BUTTONS: opt1, opt2]]

Available options (choose max 3):
- book: "Book Appointment"
- location: "Get Directions"
- doctors: "View Doctors"
- hours: "View Hours"
- emergency: "Emergency Info"
- contact: "Contact Us"

Example: "Dr. Mahesh Babu is our chief cardiologist. [[BUTTONS: book, doctors]]"

=== AUTOMATIC FALLBACK TRIGGERS ===
If user asks about these, respond with fallback:
- Medical symptoms, diagnosis, treatment, medication
- Their personal information or medical records

=== HOSPITAL INFORMATION ===
{clinic_context}

=== END OF INSTRUCTIONS ===
Remember: Focus on being a helpful guide. If they ask about doctors, give the info and suggest booking."""


def is_blocked_topic(message: str) -> bool:
    """
    Check if message contains blocked topics.
    Returns True if message should NOT go to AI.
    """
    message_lower = message.lower()
    
    for category, keywords in BLOCKED_TOPICS.items():
        for keyword in keywords:
            if keyword in message_lower:
                logger.info(f"Blocked topic detected: {category}/{keyword}")
                return True
    
    return False


def is_allowed_for_ai(message: str) -> bool:
    """
    Check if message is safe to send to AI.
    Returns True only if message passes all safety checks.
    """
    # Check for medical queries
    if contains_medical_query(message):
        return False
    
    # Check for blocked topics
    if is_blocked_topic(message):
        return False
    
    return True


def get_ai_response(user_message: str, clinic_id: str = None, user_id: str = None, crm_context: str = "") -> dict:
    """
    Get AI response for general questions only.
    
    Returns:
        Dictionary: {
            'text': str,
            'buttons': list of dict [{'id': '...', 'title': '...'}]
        }
    """
    # Pre-check: Is this allowed for AI?
    if not is_allowed_for_ai(user_message):
        logger.info(f"Message blocked from AI (pre-check): {user_message[:50]}...")
        return {'text': FALLBACK_MESSAGE, 'buttons': []}
    
    # Sanitize input - remove any personal data
    sanitized_message = sanitize_for_ai(user_message)
    
    # Check if API key is configured
    if not _api_key:
        logger.warning("Gemini API key not configured")
        return {'text': FALLBACK_MESSAGE, 'buttons': []}
    
    try:
        # Get clinic FAQ context
        clinic = get_clinic_config(clinic_id)
        clinic_context = clinic.get('faq_data', '')
        
        if not clinic_context:
            logger.warning("No FAQ data available for clinic")
            return {'text': FALLBACK_MESSAGE, 'buttons': []}
        
        # Build prompt with strict instructions
        system_prompt = _build_system_prompt(clinic_context, crm_context)
        full_prompt = f"{system_prompt}\n\nUser question: {sanitized_message}\n\nYour response:"
        
        # Initialize model
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config=GENERATION_CONFIG
        )
        
        # Generate response
        response = model.generate_content(
            full_prompt,
            request_options={'timeout': REQUEST_TIMEOUT}
        )
        
        if not response or not response.text:
            return {'text': FALLBACK_MESSAGE, 'buttons': []}
        
        raw_text = response.text.strip()
        
        # Log interaction
        logger.info(f"AI Output: {raw_text}")
        
        # Parse buttons
        text, buttons = _parse_interactive_response(raw_text)
        
        # Post-validation: Check if text is safe
        if not _validate_response(text):
            logger.warning(f"AI response failed validation: {text[:100]}...")
            return {'text': FALLBACK_MESSAGE, 'buttons': []}
        
        # Log successful interaction
        log_ai_interaction(user_id, sanitized_message, raw_text, True)
        
        return {
            'text': text,
            'buttons': buttons
        }
        
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        log_ai_interaction(user_id, sanitized_message, f"[ERROR: {str(e)}]", False)
        return {'text': FALLBACK_MESSAGE, 'buttons': []}


def _parse_interactive_response(raw_text: str) -> tuple:
    """
    Extract buttons from AI response.
    Format: [[BUTTONS: key1, key2]]
    """
    import re
    
    # Extract text and button tags
    button_match = re.search(r'\[\[BUTTONS:\s*(.*?)\]\]', raw_text)
    
    # Map AI keywords to real button IDs and titles
    BUTTON_MAP = {
        'book': {'id': 'start_booking', 'title': '📅 Book Now'},
        'location': {'id': 'address', 'title': '📍 Location'},
        'doctors': {'id': 'doctors', 'title': '👨‍⚕️ Our Doctors'},
        'hours': {'id': 'hours', 'title': '🕐 Opening Hours'},
        'emergency': {'id': 'emergency', 'title': '🚑 Emergency'},
        'contact': {'id': 'contact', 'title': '📞 Contact Us'}
    }
    
    buttons = []
    text = raw_text
    
    if button_match:
        # Remove tag from text
        text = raw_text.replace(button_match.group(0), '').strip()
        
        # Parse choices
        choices = [c.strip().lower() for c in button_match.group(1).split(',')]
        
        for choice in choices:
            if choice in BUTTON_MAP:
                buttons.append(BUTTON_MAP[choice])
    
    # Limit to 3 buttons (WhatsApp requirement)
    return text, buttons[:3]


def _validate_response(response: str) -> bool:
    """
    Validate AI response is safe and appropriate.
    Returns False if response should be blocked.
    """
    response_lower = response.lower()
    
    # Check for medical advice indicators
    medical_phrases = [
        'you should take', 'i recommend taking', 'prescription',
        'dosage', 'mg', 'twice a day', 'diagnosis is', 'treatment for',
        'medicine for', 'take this', 'medication', 'consult a doctor about'
    ]
    if any(phrase in response_lower for phrase in medical_phrases):
        logger.warning("Response contains medical advice")
        return False
    
    # Check for uncertainty/hallucination indicators
    uncertain_phrases = [
        'i think', 'probably', 'might be', 'i believe', 'i assume',
        'i guess', 'perhaps', 'possibly', 'it seems', 'likely'
    ]
    if any(phrase in response_lower for phrase in uncertain_phrases):
        logger.warning("Response contains uncertain language")
        return False
    
    # Check for follow-up questions
    question_indicators = [
        'can you tell me', 'what is your', 'could you provide',
        'do you have', 'would you like', 'shall i', 'can i ask'
    ]
    if any(phrase in response_lower for phrase in question_indicators):
        logger.warning("Response contains follow-up questions")
        return False
    
    # Check for appointment confirmation language
    booking_phrases = [
        'your appointment', 'booked for', 'confirmed for',
        'scheduled for', 'reservation', 'appointment is'
    ]
    if any(phrase in response_lower for phrase in booking_phrases):
        logger.warning("Response contains booking language")
        return False
    
    # Response should not be too long
    if len(response) > 400:
        logger.warning("Response too long")
        return False
    
    # Response should not be empty or just whitespace
    if not response.strip():
        return False
    
    return True
