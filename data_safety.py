"""
Data Safety Module
Ensures no personal data is sent to AI.
All sanitization happens BEFORE any AI call.
"""

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def mask_phone_numbers(text: str) -> str:
    """
    Mask phone numbers in text.
    Handles various international formats.
    """
    patterns = [
        # International format: +1-234-567-8900, +91 98765 43210
        r'\+?\d{1,3}[-.\s]?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}',
        # Simple 10-12 digit numbers
        r'\b\d{10,12}\b',
        # Format: (123) 456-7890
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
    ]
    
    masked = text
    for pattern in patterns:
        masked = re.sub(pattern, '[PHONE]', masked)
    
    return masked


def mask_email(text: str) -> str:
    """Mask email addresses in text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.sub(pattern, '[EMAIL]', text)


def mask_names(text: str, known_names: Optional[List[str]] = None) -> str:
    """
    Mask known names in text.
    Only masks explicitly provided names.
    """
    if not known_names:
        return text
    
    masked = text
    for name in known_names:
        if name and len(name) >= 2:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(name), re.IGNORECASE)
            masked = pattern.sub('[NAME]', masked)
    
    return masked


def mask_booking_ids(text: str) -> str:
    """Mask booking IDs in text."""
    # Pattern: APT followed by digits
    pattern = r'APT\d{6,10}'
    return re.sub(pattern, '[BOOKING_ID]', text, flags=re.IGNORECASE)


def sanitize_for_ai(text: str, patient_name: Optional[str] = None) -> str:
    """
    Sanitize text before sending to AI.
    Removes all personally identifiable information.
    
    Args:
        text: Original user message
        patient_name: Optional known patient name to mask
    
    Returns:
        Sanitized text safe for AI processing
    """
    sanitized = text
    
    # Apply all masking functions
    sanitized = mask_phone_numbers(sanitized)
    sanitized = mask_email(sanitized)
    sanitized = mask_booking_ids(sanitized)
    
    if patient_name:
        sanitized = mask_names(sanitized, [patient_name])
    
    # Log if anything was masked
    if sanitized != text:
        logger.debug(f"Sanitized: '{text[:50]}...' -> '{sanitized[:50]}...'")
    
    return sanitized


def contains_personal_data(text: str) -> bool:
    """
    Check if text contains obvious personal data.
    """
    # Check for phone patterns
    phone_patterns = [
        r'\+?\d{10,}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]
    for pattern in phone_patterns:
        if re.search(pattern, text):
            return True
    
    # Check for email
    if re.search(r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
        return True
    
    return False


def contains_medical_query(text: str) -> bool:
    """
    Check if text contains medical advice requests.
    These should NEVER be sent to AI.
    
    Returns:
        True if text contains medical query indicators
    """
    medical_keywords = [
        # Symptoms
        'symptom', 'symptoms', 'pain', 'ache', 'fever', 'cough',
        'headache', 'nausea', 'vomiting', 'diarrhea', 'rash',
        'swelling', 'bleeding', 'dizzy', 'fatigue', 'weakness',
        
        # Diagnosis
        'diagnosis', 'diagnose', 'what do i have', 'am i sick',
        'is it serious', 'what is wrong', 'what\'s wrong',
        
        # Treatment
        'treatment', 'cure', 'how to treat', 'remedy', 'heal',
        
        # Medication
        'medicine', 'medication', 'drug', 'prescription', 'dose',
        'dosage', 'tablet', 'pill', 'capsule', 'syrup',
        'should i take', 'can i take', 'what medicine',
        
        # Medical advice
        'medical advice', 'health advice', 'should i see',
        'is it normal', 'side effect', 'allergic', 'allergy',
    ]
    
    text_lower = text.lower()
    
    for keyword in medical_keywords:
        if keyword in text_lower:
            logger.debug(f"Medical keyword detected: {keyword}")
            return True
    
    return False


def is_safe_for_logging(text: str) -> str:
    """
    Make text safe for logging by masking PII.
    """
    safe = mask_phone_numbers(text)
    safe = mask_email(safe)
    return safe
