"""
Instagram Messaging API Client
Sends replies via Graph API using PAGE_ID and PAGE_ACCESS_TOKEN.
Uses same webhook as WhatsApp; channel is detected by messaging_product.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


def _get_credentials() -> tuple:
    """Get Instagram API credentials."""
    page_id = os.getenv('INSTAGRAM_PAGE_ID')
    token = os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN')
    return page_id, token


def send_text_message(recipient_id: str, text: str) -> bool:
    """
    Send a text message via Instagram Messaging API (Graph API).

    POST https://graph.facebook.com/v18.0/{PAGE_ID}/messages
    Body: messaging_product, recipient.id, message.text.body
    """
    page_id, token = _get_credentials()

    if not page_id or not token:
        logger.error("Instagram credentials not configured (INSTAGRAM_PAGE_ID, INSTAGRAM_PAGE_ACCESS_TOKEN)")
        return False

    url = f"{GRAPH_API_URL}/{page_id}/messages"

    payload = {
        "messaging_product": "instagram",
        "recipient": {"id": str(recipient_id)},
        "message": {"text": text}
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            logger.info(f"Instagram text message sent to {str(recipient_id)[:8]}***")
            return True
        logger.error(f"Instagram API error: {response.status_code} - {response.text}")
        return False
    except requests.RequestException as e:
        logger.error(f"Instagram request failed: {str(e)}")
        return False
