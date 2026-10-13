# Sudha Staff Dashboard

Staff inbox for all WhatsApp requests:
- Appointments
- IPD enquiries
- Pharmacy prescriptions / alerts
- Staff notifications

## Local run

Terminal 1 (API):
```bash
cd D:\sudha_hospital_whatsapp
python app.py
```

Terminal 2 (UI):
```bash
cd D:\sudha_hospital_whatsapp\dashboard
npm install
npm run dev
```

Open: http://localhost:5173  
Login: `admin` / `sudha123`

## Production (AWS)

```bash
cd ~/sudha_whatsapp
git pull
source .venv/bin/activate

cd dashboard
npm install
npm run build
cd ..

sudo systemctl restart sudha-whatsapp
```

Open: **https://chat.sudhahospitalkphb.com/crm/**  
Login: `admin` / `sudha123`

## API used by inbox

- `GET /api/staff/requests`
- `GET /api/enquiries`
- `GET /api/pharmacy`
- `GET /api/staff/notifications`
- `PUT /api/enquiries/<id>/status`
- `PUT /api/pharmacy/<id>/status`
- `PUT /api/appointments/<id>/status`
