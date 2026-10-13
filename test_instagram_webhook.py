#!/usr/bin/env python3
"""
Test Instagram webhook without touching WhatsApp.
Sends a mock POST to /webhook with object=instagram, entry[].messaging[].
Run app first: python app.py
Then: python test_instagram_webhook.py
"""

import requests
import json

# Mock Instagram payload: object=instagram, entry[].messaging[]
# Same structure as Meta sends for Instagram Messaging (Messenger-style)
payload = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841440354346213",
            "time": 1234567890,
            "messaging": [
                {
                    "sender": {"id": "12345678901234567"},
                    "recipient": {"id": "17841440354346213"},
                    "timestamp": 1234567890123,
                    "message": {
                        "mid": "mid.xxx",
                        "text": "hi"
                    }
                }
            ]
        }
    ]
}

URL = "http://127.0.0.1:8000/webhook"

def main():
    print("Sending mock Instagram webhook POST to", URL)
    print("Payload object:", payload["object"])
    print("Message text:", payload["entry"][0]["messaging"][0]["message"]["text"])
    print("-" * 50)
    r = requests.post(URL, json=payload, timeout=10)
    print("Status:", r.status_code)
    print("Response:", r.text)
    if r.status_code == 200:
        print("\nWebhook returned 200 OK. Check app logs for:")
        print("  - RAW BODY / PARSED JSON")
        print("  - OBJECT: instagram")
        print("  - Message from ... : hi")
        print("  - Text message sent to ... (if token works)")
    else:
        print("\nUnexpected status. Check server logs.")

if __name__ == "__main__":
    main()
