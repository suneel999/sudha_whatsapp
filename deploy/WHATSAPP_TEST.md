# Sudha WhatsApp test (nginx + Meta test number)

## 1. Create `.env`

```bash
cd D:\sudha_hospital_whatsapp
copy .env.example .env
```

Fill at least:

```env
WHATSAPP_TOKEN=EAAxxxx...                 # From Meta App → WhatsApp → API Setup
WHATSAPP_PHONE_NUMBER_ID=1234567890       # Test number Phone number ID
WEBHOOK_VERIFY_TOKEN=sudha_verify_token   # Any secret you choose
PORT=8000
DEBUG=true
```

## 2. Run the bot locally

```bash
cd D:\sudha_hospital_whatsapp
pip install -r requirements.txt
python app.py
```

Check: open `http://127.0.0.1:8000/health` → should return OK/JSON.

## 3. nginx

1. Copy `deploy/nginx-sudha.conf` into nginx sites (Linux example):
   - `/etc/nginx/sites-available/sudha-wa`
2. Set `server_name` to your public domain.
3. Enable + reload:
   ```bash
   sudo ln -s /etc/nginx/sites-available/sudha-wa /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Add HTTPS (recommended for Meta):
   ```bash
   sudo certbot --nginx -d YOUR_DOMAIN_HERE
   ```

Public webhook URL:

```text
https://YOUR_DOMAIN_HERE/webhook
```

## 4. Meta Developer → WhatsApp webhook

1. Meta App → **WhatsApp** → **Configuration** (or API Setup → Webhook)
2. Callback URL: `https://YOUR_DOMAIN_HERE/webhook`
3. Verify token: same as `WEBHOOK_VERIFY_TOKEN` in `.env` (e.g. `sudha_verify_token`)
4. Subscribe to: **messages** (and optionally `message_deliveries`)
5. Click **Verify and save**

If verify fails:
- bot not running on `:8000`
- nginx not proxying `/webhook`
- verify token mismatch
- no HTTPS / wrong domain

## 5. Test number checklist

1. In Meta → WhatsApp → **API Setup**, use the **Test number**
2. Add your personal WhatsApp as a **recipient** (allowed test users)
3. From your phone, message the test number: `hi`
4. You should get Sudha Hospital main menu (service list)
5. Walk one flow (OPD / Lab / Ultrasound)

## 6. Watch logs

On the server/PC running Flask:

```text
WEBHOOK HIT
Button click / Message from ...
Routing - User: ... State: MAIN_MENU
```

If webhook GET verifies but POST never appears, the message is not reaching your URL (DNS/nginx/firewall), or the sender is not added as a test recipient.

## Endpoints used

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/webhook` | Meta verify |
| POST | `/webhook` | Incoming WhatsApp messages |
| GET | `/health` | App health |
| POST | `/flow` | WhatsApp Flows (not required for Sudha button flows) |
