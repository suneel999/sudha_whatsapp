# Local test with ngrok (Sudha)

Your Flask app is already running on **port 8000**.

## 1. Start ngrok (new terminal)

```bash
ngrok http 8000
```

Copy the HTTPS URL, e.g.:

```text
https://abcd-12-34-56-78.ngrok-free.app
```

## 2. Meta webhook

In Meta App → WhatsApp → Configuration:

| Field | Value |
|--------|--------|
| Callback URL | `https://YOUR_NGROK_URL/webhook` |
| Verify token | `sudha_verify_token` |

Subscribe to **messages** → Verify and save.

## 3. Test

1. Add your phone as a WhatsApp test recipient in Meta.
2. Message the test number: `hi`
3. You should get Sudha Hospital service menu.
4. Watch Flask terminal for `WEBHOOK HIT`.

## Notes

- Keep both `python app.py` and `ngrok http 8000` running.
- Free ngrok URL changes every restart → update Meta callback URL each time.
- If Meta verify fails: confirm URL ends with `/webhook` and token is exactly `sudha_verify_token`.
