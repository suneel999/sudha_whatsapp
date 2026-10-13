# Sudha WhatsApp — Live Deploy Checklist

**Domain:** `https://chat.sudhahospitalkphb.com`  
**Webhook:** `https://chat.sudhahospitalkphb.com/webhook`  
**WhatsApp number:** +91 63098 00624 (Phone number ID `1398344433361229`)  
**Verify token:** `sudha_verify_token`  
**GitHub repo:** `https://github.com/suneel999/sudha_whatsapp`

Do these steps in order.

---

## A. You create (AWS + DNS + Meta)

### A1. AWS EC2
1. Launch **Ubuntu 22.04** EC2 (t3.small or larger).
2. Security group inbound:
   - **22** SSH (your IP)
   - **80** HTTP (0.0.0.0/0)
   - **443** HTTPS (0.0.0.0/0)
3. Attach Elastic IP (recommended).
4. Note the public IP.

### A2. DNS (sudhahospitalkphb.com)
1. Add **A record** on `sudhahospitalkphb.com`:
   - Host: `chat`
   - Value: EC2 public / Elastic IP
   - TTL: 300
2. Wait until `ping chat.sudhahospitalkphb.com` resolves to that IP.

### A3. GitHub / Git repo
Repo already exists: https://github.com/suneel999/sudha_whatsapp

### A4. Meta WhatsApp (after HTTPS works — do this last)
1. Meta Developer → your App → **WhatsApp → Configuration**
2. Callback URL: `https://chat.sudhahospitalkphb.com/webhook`
3. Verify token: `sudha_verify_token`
4. Verify and save
5. Webhook fields → subscribe **messages**
6. Make sure Phone number ID `1398344433361229` is the number connected to this app

---

## B. On the AWS server (SSH)

```bash
ssh ubuntu@YOUR_EC2_IP
```

### B1. System packages
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx git certbot python3-certbot-nginx
```

### B2. Clone code
```bash
cd /home/ubuntu
git clone https://github.com/suneel999/sudha_whatsapp.git
cd sudha_whatsapp
```

### B3. Python env
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### B4. Create `.env` on server (paste secrets here — do not commit)
```bash
nano /home/ubuntu/sudha_whatsapp/.env
```

```env
WHATSAPP_TOKEN=YOUR_PERMANENT_OR_LONG_LIVED_TOKEN
WHATSAPP_PHONE_NUMBER_ID=1398344433361229
WEBHOOK_VERIFY_TOKEN=sudha_verify_token
PORT=8000
FLASK_ENV=production
DEBUG=false
```

Save: Ctrl+O, Enter, Ctrl+X

### B5. systemd service
```bash
sudo cp deploy/sudha-whatsapp.service /etc/systemd/system/sudha-whatsapp.service
sudo systemctl daemon-reload
sudo systemctl enable sudha-whatsapp
sudo systemctl start sudha-whatsapp
sudo systemctl status sudha-whatsapp
```

Check health locally:
```bash
curl http://127.0.0.1:8000/health
```

### B6. nginx
```bash
sudo cp deploy/nginx-chat.sudhahospitalkphb.com.conf /etc/nginx/sites-available/chat.sudhahospitalkphb.com
sudo ln -sf /etc/nginx/sites-available/chat.sudhahospitalkphb.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
# remove broken old symlink if any
sudo rm -f /etc/nginx/sites-enabled/chat.sudhahospital.com
sudo nginx -t
sudo systemctl reload nginx
```

### B7. HTTPS (required for Meta)
```bash
sudo certbot --nginx -d chat.sudhahospitalkphb.com
```

Test:
```bash
curl https://chat.sudhahospitalkphb.com/health
```

---

## C. Connect Meta + test live

1. Complete **A4** (Meta webhook → `https://chat.sudhahospitalkphb.com/webhook`)
2. From your phone, message **+91 63098 00624**: `hi`
3. You should get Sudha Hospital service menu
4. Watch logs:
   ```bash
   sudo journalctl -u sudha-whatsapp -f
   ```

---

## D. Later updates

```bash
cd /home/ubuntu/sudha_whatsapp
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sudha-whatsapp
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Meta verify fails | Bot not running, nginx wrong, or verify token mismatch |
| Verify OK but no reply | Subscribe **messages**; check `journalctl -u sudha-whatsapp -f` |
| DNS not resolving | Wait for A record `chat` on sudhahospitalkphb.com |
| 502 Bad Gateway | `sudo systemctl status sudha-whatsapp` — gunicorn down |
| Token expired | Generate new token in Meta → update server `.env` → restart service |

---

## Final target

```text
WhatsApp user
    → Meta Cloud API
    → https://chat.sudhahospitalkphb.com/webhook
    → nginx → gunicorn (port 8000)
    → Sudha bot reply
```
