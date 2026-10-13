"""Diagnose WhatsApp templates + optional resend."""
import json
import os
import sys
import requests

TOKEN = os.environ["WA_TEST_TOKEN"].strip()
PHONE_ID = os.environ["WA_TEST_PHONE_ID"].strip()
TO = os.environ.get("WA_TEST_TO", "").strip().lstrip("+")
WAMID = os.environ.get("WA_TEST_WAMID", "").strip()
GRAPH = "https://graph.facebook.com/v21.0"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

print("=== Phone number ===")
r = requests.get(f"{GRAPH}/{PHONE_ID}?fields=verified_name,display_phone_number,quality_rating,webhook_configuration", headers=headers, timeout=30)
print(r.status_code, r.text[:600])

print("\n=== WABA / message templates ===")
# Get WABA id via phone number
r2 = requests.get(f"{GRAPH}/{PHONE_ID}?fields=id,account_mode", headers=headers, timeout=30)
print("phone meta:", r2.status_code, r2.text[:400])

# List templates via business account - try owned WhatsApp Business Account
r3 = requests.get(
    f"{GRAPH}/{PHONE_ID}/whatsapp_business_account",
    headers=headers,
    timeout=30,
)
print("waba link:", r3.status_code, r3.text[:600])

waba_id = None
if r3.status_code == 200:
    waba_id = (r3.json() or {}).get("id")

if not waba_id:
    # fallback: debug token / me
    r4 = requests.get(f"{GRAPH}/me?fields=id,name", headers=headers, timeout=30)
    print("me:", r4.status_code, r4.text[:400])

if waba_id:
    r5 = requests.get(
        f"{GRAPH}/{waba_id}/message_templates?limit=50",
        headers=headers,
        timeout=30,
    )
    print("templates status:", r5.status_code)
    data = r5.json() if r5.status_code == 200 else {}
    for t in data.get("data", []):
        print(f" - {t.get('name')} | lang={t.get('language')} | status={t.get('status')}")

if WAMID:
    print("\n=== Message status (if available) ===")
    # Graph often cannot fetch message by wamid directly; try anyway
    rm = requests.get(f"{GRAPH}/{WAMID}", headers=headers, timeout=30)
    print(rm.status_code, rm.text[:500])

if TO:
    print("\n=== Resend hello_world en_US ===")
    payload = {
        "messaging_product": "whatsapp",
        "to": TO,
        "type": "template",
        "template": {"name": "hello_world", "language": {"code": "en_US"}},
    }
    rs = requests.post(f"{GRAPH}/{PHONE_ID}/messages", headers=headers, json=payload, timeout=30)
    print(rs.status_code, rs.text[:800])

    print("\n=== Also try language en ===")
    payload["template"]["language"]["code"] = "en"
    rs2 = requests.post(f"{GRAPH}/{PHONE_ID}/messages", headers=headers, json=payload, timeout=30)
    print(rs2.status_code, rs2.text[:800])
