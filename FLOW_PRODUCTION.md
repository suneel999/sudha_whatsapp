# WhatsApp Flow – Production Setup

## Why you were getting old/starting data in the response

1. **Webhook ran before /flow** – Meta can send the "flow completed" webhook before your `/flow` endpoint gets the COMPLETE request. The app then looked up "latest appointment" in the DB and sometimes got the previous booking.
2. **PEM not in production** – If `private_key.pem` is missing or `PRIVATE_KEY_PATH` is wrong, the `/flow` request **cannot be decrypted**. Then:
   - No booking is saved from the Flow.
   - No confirmation is sent from `/flow`.
   - The webhook may still run and show an old booking from the DB.

**Fixes in code:** Confirmation is now sent from the **/flow COMPLETE handler** (with the exact booking that was just saved). The webhook is only a fallback. You must have the private key in production so `/flow` can decrypt and run that handler.

---

## Production checklist

### 1. PEM files (required for Flow to work)

- **Deploy `private_key.pem`** to the server (same key you used when signing the Flow in Meta Developer Dashboard).
- Set in `.env`:
  ```env
  PRIVATE_KEY_PATH=private_key.pem
  ```
  Or the full path, e.g. `/app/private_key.pem`.
- **Do not** commit `private_key.pem` to git. Add it to `.gitignore` and deploy it via secrets or a secure copy.
- If the key is missing, you will see in logs: `CRITICAL: Private key not found at ...` and Flow submissions will fail (no booking, no confirmation).

### 2. Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `FLOW_ID` | Yes (for Flow) | Your WhatsApp Flow ID from Meta. |
| `USE_FLOWS` | Optional | Flow is used when `FLOW_ID` is set. |
| `PRIVATE_KEY_PATH` | Yes (for encrypted Flow) | Path to `private_key.pem` for decrypting Flow requests. |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes | Used when sending the confirmation from the `/flow` handler. |
| `WHATSAPP_TOKEN` | Yes | WhatsApp API token. |

### 3. Verify after deploy

1. Start the app and check logs for:
   - No `CRITICAL: Private key not found` (if you see it, fix `PRIVATE_KEY_PATH` and the file).
2. Book an appointment via the Flow and confirm:
   - The confirmation message shows the **same** doctor, date, time and booking ID you just selected.
3. If confirmation still shows old data:
   - Ensure only one worker/process is used when testing (e.g. `gunicorn -w 1`), or that the server can reach the same DB and that `/flow` is really decrypting (no 421 from `/flow`).

---

## Summary

- **Update PEM in production:** Copy `private_key.pem` to the server and set `PRIVATE_KEY_PATH` in `.env`. This is required for Flow requests to be decrypted and for the correct booking + confirmation to be created and sent from `/flow`.
- **Confirmation is sent from /flow** with the booking that was just saved; the webhook is only a fallback. So once PEM and env are correct, the response data should match the Flow submission.
