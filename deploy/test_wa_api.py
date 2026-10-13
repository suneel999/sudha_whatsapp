"""One-off WhatsApp Cloud API credential + hello_world template test."""
import json
import os
import sys
import requests

TOKEN = os.environ.get("WA_TEST_TOKEN", "").strip()
PHONE_NUMBER_ID = os.environ.get("WA_TEST_PHONE_ID", "").strip()
TO = os.environ.get("WA_TEST_TO", "917981982040").strip().lstrip("+")

GRAPH = "https://graph.facebook.com/v21.0"

if not TOKEN or not PHONE_NUMBER_ID:
    print("Missing WA_TEST_TOKEN or WA_TEST_PHONE_ID")
    sys.exit(1)

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

print("1) Checking phone number ID...")
r = requests.get(f"{GRAPH}/{PHONE_NUMBER_ID}", headers=headers, timeout=30)
print("GET status:", r.status_code)
print(r.text[:800])
if r.status_code != 200:
    print("FAILED: token or phone number id invalid")
    sys.exit(1)

print("\n2) Sending hello_world template to", TO, "...")
payload = {
    "messaging_product": "whatsapp",
    "to": TO,
    "type": "template",
    "template": {"name": "hello_world", "language": {"code": "en_US"}},
}
r2 = requests.post(
    f"{GRAPH}/{PHONE_NUMBER_ID}/messages",
    headers=headers,
    json=payload,
    timeout=30,
)
print("POST status:", r2.status_code)
print(r2.text[:1200])
if r2.status_code == 200:
    print("\nSUCCESS: API working. Check WhatsApp on", TO)
else:
    print("\nFAILED: could not send template")
    sys.exit(1)
