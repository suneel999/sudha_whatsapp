"""
WhatsApp Cloud API Client
Handles all WhatsApp message sending with interactive buttons.

=============================================================================
ENTERPRISE-GRADE BUTTON-BASED MESSAGING
=============================================================================

This client supports:
1. Interactive reply buttons (max 3 buttons per message)
2. Interactive list messages (for more options)
3. Call-to-action buttons (phone call, URL)
4. Text messages (for confirmations and info)

CRITICAL: All decision points MUST use interactive buttons.
Users should NEVER have to type numbers.

=============================================================================
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


def _get_credentials(phone_number_id: str = None) -> tuple:
    """Get WhatsApp API credentials."""
    phone_number_id = phone_number_id or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    token = os.getenv('WHATSAPP_TOKEN')
    return phone_number_id, token


def _make_request(url: str, payload: dict, timeout: int = 30) -> bool:
    """Make API request to WhatsApp."""
    _, token = _get_credentials()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return False


def send_text_message(to: str, message: str, phone_number_id: str = None) -> bool:
    """
    Send a text message via WhatsApp Cloud API.
    
    Use this for:
    - Confirmation messages
    - Information responses
    - Error messages
    
    Do NOT use for menus - use send_interactive_buttons instead.
    """
    phone_number_id, token = _get_credentials(phone_number_id)
    
    if not phone_number_id or not token:
        logger.error("WhatsApp credentials not configured")
        return False
    
    # Clean phone number for Meta Cloud API
    to = str(to).strip().lstrip('+').replace(' ', '')
    
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'text',
        'text': {'body': message}
    }
    
    success = _make_request(url, payload)
    if success:
        logger.info(f"Text message sent to {to[:6]}***")
    return success


def send_interactive_buttons(
    to: str, 
    body: str, 
    buttons: List[Dict[str, str]], 
    phone_number_id: str = None,
    header: str = None,
    footer: str = None
) -> bool:
    """
    Send interactive button message.
    
    CRITICAL: This is the PRIMARY method for all decision points.
    
    Args:
        to: Recipient phone number
        body: Message body text
        buttons: List of button dicts with 'id' (payload) and 'title' (display text)
                 Example: [{'id': 'MENU_APPOINTMENT', 'title': '📅 Book Appointment'}]
        phone_number_id: WhatsApp phone number ID
        header: Optional header text
        footer: Optional footer text
    
    Returns:
        True if sent successfully
    
    Note:
        - Maximum 3 buttons per message
        - Button titles max 20 characters
        - Button IDs are used for routing (payloads)
    """
    phone_number_id, token = _get_credentials(phone_number_id)
    
    if not phone_number_id or not token:
        logger.error("WhatsApp credentials not configured")
        return False
    
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    
    # Build button list (max 3 buttons, max 20 chars per title)
    button_list = []
    for btn in buttons[:3]:
        button_list.append({
            'type': 'reply',
            'reply': {
                'id': btn['id'],
                'title': btn['title'][:20]
            }
        })
    
    # Build interactive object
    interactive = {
        'type': 'button',
        'body': {'text': body},
        'action': {'buttons': button_list}
    }
    
    # Add optional header
    if header:
        interactive['header'] = {
            'type': 'text',
            'text': header[:60]  # Max 60 chars
        }
    
    # Add optional footer
    if footer:
        interactive['footer'] = {
            'text': footer[:60]  # Max 60 chars
        }
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'interactive',
        'interactive': interactive
    }
    
    success = _make_request(url, payload)
    if success:
        logger.info(f"Interactive buttons sent to {to[:6]}*** - {len(button_list)} buttons")
    return success


def send_interactive_list(
    to: str, 
    body: str, 
    button_text: str, 
    sections: List[Dict[str, Any]], 
    phone_number_id: str = None,
    header: str = None,
    footer: str = None
) -> bool:
    """
    Send interactive list message.
    
    Use this when you need more than 3 options (e.g., 7 diagnostic tests).
    
    Args:
        to: Recipient phone number
        body: Message body text
        button_text: Text on the button that opens the list
        sections: List of section dicts with 'title' and 'rows'
                  rows: List of {'id': 'payload', 'title': 'Display', 'description': 'Optional desc'}
        phone_number_id: WhatsApp phone number ID
        header: Optional header text
        footer: Optional footer text
    
    Returns:
        True if sent successfully
    
    Note:
        - Maximum 10 rows per section (WhatsApp Cloud API limit)
        - Row titles max 24 characters, descriptions max 72
    """
    phone_number_id, token = _get_credentials(phone_number_id)
    
    if not phone_number_id or not token:
        logger.error("WhatsApp credentials not configured")
        return False
    
    # Meta: max 10 rows/section; section title 24 chars; row title 24 chars; row description 72 chars
    safe_sections = []
    for sec in sections:
        raw_rows = (sec.get('rows') or [])[:10]
        if not raw_rows:
            continue
        rows = []
        for r in raw_rows:
            row = {'id': str(r.get('id', ''))[:200], 'title': str(r.get('title', ''))[:24]}
            if r.get('description'):
                row['description'] = str(r.get('description', ''))[:72]
            rows.append(row)
        safe_sections.append({
            'title': (sec.get('title') or 'Options')[:24],
            'rows': rows
        })
    
    if not safe_sections:
        logger.warning("Interactive list has no valid sections/rows")
        return False
    
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    
    # Build interactive object
    interactive = {
        'type': 'list',
        'body': {'text': body},
        'action': {
            'button': button_text[:20],
            'sections': safe_sections
        }
    }
    
    # Add optional header
    if header:
        interactive['header'] = {
            'type': 'text',
            'text': header[:60]
        }
    
    # Add optional footer
    if footer:
        interactive['footer'] = {
            'text': footer[:60]
        }
    
    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'interactive',
        'interactive': interactive
    }
    
    success = _make_request(url, payload)
    if success:
        logger.info(f"Interactive list sent to {to[:6]}***")
    return success


def send_call_to_action(
    to: str,
    body: str,
    buttons: List[Dict[str, str]],
    phone_number_id: str = None,
    header: str = None,
    footer: str = None
) -> bool:
    """
    Send call-to-action button message (phone call or URL).
    
    Use this for emergency contact buttons.
    
    Args:
        to: Recipient phone number
        body: Message body text
        buttons: List of CTA button dicts:
                 - Phone: {'type': 'phone', 'text': 'Call Now', 'phone': '+919885454128'}
                 - URL: {'type': 'url', 'text': 'Visit Website', 'url': 'https://...'}
        phone_number_id: WhatsApp phone number ID
        header: Optional header text
        footer: Optional footer text
    
    Returns:
        True if sent successfully
    
    Note: This uses template messages which may require approval.
          For now, we'll use a workaround with text + reply buttons.
    """
    # Note: True CTA buttons require pre-approved templates
    # For now, we send a text message with the phone number prominently displayed
    # and use reply buttons for navigation
    
    phone_number_id, token = _get_credentials(phone_number_id)
    
    if not phone_number_id or not token:
        logger.error("WhatsApp credentials not configured")
        return False
    
    # Build message with clickable phone number
    message_parts = [body]
    for btn in buttons:
        if btn.get('type') == 'phone':
            message_parts.append(f"\n📞 *Call Now:* {btn.get('phone', '')}")
        elif btn.get('type') == 'url':
            message_parts.append(f"\n🔗 {btn.get('url', '')}")
    
    return send_text_message(to, '\n'.join(message_parts), phone_number_id)


def send_text_with_buttons(
    to: str,
    body: str,
    buttons: List[Dict[str, str]],
    phone_number_id: str = None
) -> bool:
    """
    Convenience function: Send text message followed by buttons.
    
    Use when you need to send a longer message with buttons
    (since button messages have limited body text).
    """
    # Send text first
    text_sent = send_text_message(to, body, phone_number_id)
    
    if not text_sent:
        return False
    
    # Then send buttons with short prompt
    return send_interactive_buttons(
        to,
        "Please select an option:",
        buttons,
        phone_number_id
    )


def mark_as_read(message_id: str, phone_number_id: str = None) -> bool:
    """Mark message as read."""
    phone_number_id, token = _get_credentials(phone_number_id)
    
    if not phone_number_id or not token:
        return False
    
    url = f"{GRAPH_API_URL}/{phone_number_id}/messages"
    
    payload = {
        'messaging_product': 'whatsapp',
        'status': 'read',
        'message_id': message_id
    }
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False


# =============================================================================
# CONVENIENCE FUNCTIONS FOR COMMON BUTTON PATTERNS
# =============================================================================

def send_main_menu_buttons(to: str, clinic_name: str, phone_number_id: str = None) -> bool:
    """
    Send the main menu with 3 service buttons.
    
    This is the ENTRY POINT for all conversations.
    """
    from button_payloads import MainMenuPayload
    
    body = f"Welcome to *{clinic_name}*! 🏥\n\nHow can we help you today?"
    
    buttons = [
        {'id': MainMenuPayload.APPOINTMENT, 'title': '📅 Book Appointment'},
        {'id': MainMenuPayload.DIAGNOSTICS, 'title': '🧪 Diagnostics'},
        {'id': MainMenuPayload.ADMISSION, 'title': '🏥 Admission'}
    ]
    
    return send_interactive_buttons(
        to, 
        body, 
        buttons, 
        phone_number_id,
        footer="Tap a button to continue"
    )


def send_confirmation_buttons(
    to: str, 
    body: str, 
    confirm_payload: str,
    cancel_payload: str,
    phone_number_id: str = None
) -> bool:
    """
    Send YES/NO confirmation buttons.
    
    Use this for all confirmation steps.
    """
    buttons = [
        {'id': confirm_payload, 'title': '✅ Confirm'},
        {'id': cancel_payload, 'title': '❌ Cancel'}
    ]
    
    return send_interactive_buttons(to, body, buttons, phone_number_id)


def send_back_to_menu_button(to: str, body: str, phone_number_id: str = None) -> bool:
    """
    Send a message with a back-to-menu button.
    
    Use after completing a flow or when user cancels.
    """
    from button_payloads import GlobalPayload
    
    buttons = [
        {'id': GlobalPayload.MAIN_MENU, 'title': '🏠 Main Menu'}
    ]
    
    return send_interactive_buttons(to, body, buttons, phone_number_id)
