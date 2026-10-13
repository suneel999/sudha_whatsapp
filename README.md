# Sudha Hospital WhatsApp Bot

Conversational WhatsApp assistant for **Sudha Hospital**. Built as a separate copy of the Mallika WhatsApp automation project — the original repo is unchanged.

## What patients can do

1. **Out Patient Services** — collect details, choose concern (Pregnancy / Menstrual / Infertility / Menopause), book appointment  
2. **Ultrasound Scanning** — pregnant / non-pregnant scans, book appointment  
3. **Lab Services** — select test, book appointment  
4. **Pharmacy** — medicine availability, prescription upload, contact pharmacist  
5. **In Patient Services** — admission / room / insurance / billing / reception enquiry  

Bookings are saved to SQLite and staff are notified via `staff_notifications`.

## Quick start

```bash
cd D:\sudha_hospital_whatsapp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with Sudha WhatsApp Cloud API credentials
python app.py
```

Health check: `GET /health`

CRM login (local default): `admin` / `sudha123`

## Main menu

Bot sends:

> 👋 Welcome to Sudha Hospital.  
> Please choose a service.

Options (interactive list):

- Out Patient Services  
- Ultrasound Scanning  
- Lab Services  
- Pharmacy  
- In Patient Services  

## Architecture

| Module | Role |
|--------|------|
| `app.py` | Flask webhook + WhatsApp send |
| `message_router.py` | State + payload routing |
| `state_machine.py` | Session / sub-states |
| `button_payloads.py` | Stable button IDs |
| `handlers/*` | OPD, Ultrasound, Lab, Pharmacy, IPD |
| `database.py` | Appointments, enquiries, prescriptions, notifications |
| `config.py` | Sudha Hospital clinic config |

## Smoke test (no WhatsApp needed)

```bash
python test_sudha_flows.py
```

## Notes

- WhatsApp allows max **3 reply buttons**; menus with more options use **list messages**.  
- Prescription upload expects an **image** while in Pharmacy → Upload Prescription.  
- Appointment confirmation offers **Modify / Cancel / Main Menu**.  
- Keep `private_key.pem` only if you later enable WhatsApp Flows (not required for current button flows).
