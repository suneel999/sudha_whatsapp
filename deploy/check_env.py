from dotenv import load_dotenv
import os

load_dotenv()
keys = ["WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WEBHOOK_VERIFY_TOKEN", "PORT"]
for k in keys:
    v = os.getenv(k) or ""
    ok = bool(v) and not v.startswith("your_")
    print(f"{k}: {'OK' if ok else 'MISSING_OR_PLACEHOLDER'}")
print("VERIFY_TOKEN_VALUE:", os.getenv("WEBHOOK_VERIFY_TOKEN") or "(empty)")
