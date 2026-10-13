# Sudha WhatsApp — Live Deploy Checklist

**Domain:** `https://chat.sudhahospital.com`  
**Webhook:** `https://chat.sudhahospital.com/webhook`  
**WhatsApp number:** +91 63098 00624 (Phone number ID `1398344433361229`)  
**Verify token:** `sudha_verify_token`

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

### A2. DNS (where sudhahospital.com is managed)
1. Add **A record**:
   - Host: `chat`
   - Value: EC2 public / Elastic IP
   - TTL: 300
2. Wait until `ping chat.sudhahospital.com` resolves to that IP.

### A3. GitHub / Git repo
1. Create empty GitHub repo: `sudha_hospital_whatsapp` (private recommended).
2. On your PC (project folder already prepared):
   ```bash
   cd D:\sudha_hospital_whatsapp
   git init -b main
   git add .
   git commit -m "Initial Sudha Hospital WhatsApp bot"
   git remote add origin https://github.com/YOUR_USER/sudha_hospital_whatsapp.git
   git push -u origin main
   ```
3. **Never commit `.env`** (already in `.gitignore`).

### A4. Meta WhatsApp (after HTTPS works — do this last)
1. Meta Developer → your App → **WhatsApp → Configuration**
2. Callback URL: `https://chat.sudhahospital.com/webhook`
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
git clone https://github.com/YOUR_USER/sudha_hospital_whatsapp.git
cd sudha_hospital_whatsapp
```

### B3. Python env
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### B4. Create `.env` on server (paste secrets here — do not commit)
```bash
nano /home/ubuntu/sudha_hospital_whatsapp/.env
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
sudo cp deploy/nginx-chat.sudhahospital.com.conf /etc/nginx/sites-available/chat.sudhahospital.com
sudo ln -sf /etc/nginx/sites-available/chat.sudhahospital.com /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### B7. HTTPS (required for Meta)
```bash
sudo certbot --nginx -d chat.sudhahospital.com
```

Test:
```bash
curl https://chat.sudhahospital.com/health
```

---

## C. Connect Meta + test live

1. Complete **A4** (Meta webhook → `https://chat.sudhahospital.com/webhook`)
2. From your phone, message **+91 63098 00624**: `hi`
3. You should get Sudha Hospital service menu
4. Watch logs:
   ```bash
   sudo journalctl -u sudha-whatsapp -f
   ```

---

## D. Later updates

```bash
cd /home/ubuntu/sudha_hospital_whatsapp
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
| DNS not resolving | Wait for A record; check Elastic IP |
| 502 Bad Gateway | `sudo systemctl status sudha-whatsapp` — gunicorn down |
| Token expired | Generate new token in Meta → update server `.env` → restart service |

---

## Final target

```text
WhatsApp user
    → Meta Cloud API
    → https://chat.sudhahospital.com/webhook
    → nginx → gunicorn (port 8000)
    → Sudha bot reply
```
