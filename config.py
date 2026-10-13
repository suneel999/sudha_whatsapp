"""
Clinic Configuration
Sudha Hospital - WhatsApp Patient Assistant
"""

MAIN_MENU_OPTIONS = {
    "opd": ["1", "opd", "out patient", "outpatient", "consultation"],
    "ultrasound": ["2", "ultrasound", "scan", "usg"],
    "lab": ["3", "lab", "laboratory", "test", "blood"],
    "pharmacy": ["4", "pharmacy", "medicine", "prescription"],
    "ipd": ["5", "ipd", "in patient", "inpatient", "admission", "room", "billing"],
}

OPD_CONCERNS = [
    {"id": "pregnancy", "name": "Pregnancy"},
    {"id": "menstrual", "name": "Menstrual Problems"},
    {"id": "infertility", "name": "Infertility"},
    {"id": "menopause", "name": "Menopause"},
]

PREGNANT_SCANS = [
    {"id": "location", "name": "Location of Pregnancy Scan"},
    {"id": "cardiac", "name": "Cardiac Activity Scan"},
    {"id": "nt", "name": "NT Scan"},
    {"id": "tiffa", "name": "TIFFA Scan"},
    {"id": "growth", "name": "Growth Scan"},
    {"id": "growth_doppler", "name": "Growth Doppler"},
]

NON_PREGNANT_SCANS = [
    {"id": "pelvis", "name": "Pelvis Scan"},
    {"id": "abd_pelvis", "name": "Whole Abdomen + Pelvis"},
    {"id": "follicular", "name": "Follicular Study"},
]

LAB_TESTS = [
    {"id": "blood", "name": "Blood Test"},
    {"id": "thyroid", "name": "Thyroid"},
    {"id": "sugar", "name": "Sugar"},
    {"id": "urine", "name": "Urine Test"},
    {"id": "cbc", "name": "CBC"},
    {"id": "others", "name": "Others"},
]

MENSTRUAL_SYMPTOMS = [
    {"id": "irregular", "name": "Irregular periods"},
    {"id": "heavy", "name": "Heavy bleeding"},
    {"id": "painful", "name": "Painful periods"},
    {"id": "missed", "name": "Missed periods"},
]

IPD_ENQUIRIES = [
    {"id": "admission", "name": "Admission Enquiry"},
    {"id": "room", "name": "Room Availability"},
    {"id": "insurance", "name": "Insurance"},
    {"id": "billing", "name": "Billing"},
    {"id": "reception", "name": "Contact Reception"},
]

CLINICS = {
    "default": {
        "name": "Sudha Hospital",
        "type": "Women & Multi-specialty Hospital",
        "phone": "+91 90000 00000",
        "alternate_phone": "+91 90000 00001",
        "email": "info@sudhahospital.com",
        "website": "https://sudhahospital.com",
        "address": "Sudha Hospital",
        "hours": "OPD: Mon-Sat 9:00 AM - 7:00 PM | Emergency: 24x7",
        "time_slots": [
            "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
            "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
            "05:00 PM", "05:30 PM", "06:00 PM",
        ],
        "services": [
            "Out Patient Services",
            "Ultrasound Scanning",
            "Lab Services",
            "Pharmacy",
            "In Patient Services",
        ],
        "opd_concerns": OPD_CONCERNS,
        "pregnant_scans": PREGNANT_SCANS,
        "non_pregnant_scans": NON_PREGNANT_SCANS,
        "lab_tests": LAB_TESTS,
        "menstrual_symptoms": MENSTRUAL_SYMPTOMS,
        "ipd_enquiries": IPD_ENQUIRIES,
        "faq_data": """
SUDHA HOSPITAL - Patient Information

SERVICES:
- Out Patient Services (Pregnancy, Menstrual Problems, Infertility, Menopause)
- Ultrasound Scanning (Pregnant & Non Pregnant)
- Lab Services (Blood, Thyroid, Sugar, Urine, CBC, Others)
- Pharmacy (Medicine availability, Prescription upload, Pharmacist contact)
- In Patient Services (Admission, Rooms, Insurance, Billing, Reception)

HOURS:
- OPD: Monday to Saturday 9:00 AM to 7:00 PM
- Emergency / In-patient support: 24x7

BOOKING:
Patients can book appointments via WhatsApp bot and receive a reference number.
Staff are notified for new bookings, pharmacy uploads, and IPD enquiries.
""",
    }
}


def get_clinic_config(phone_number_id: str = None) -> dict:
    """Returns clinic config. Extend this to map phone_number_id to clinic."""
    return CLINICS["default"]


def get_main_menu_keywords() -> dict:
    """Returns main menu option keywords."""
    return MAIN_MENU_OPTIONS


def get_diagnostics_tests() -> list:
    """Compatibility helper (legacy imports / flow checks)."""
    return LAB_TESTS


def get_admission_types() -> list:
    """Compatibility helper for IPD enquiry types."""
    return IPD_ENQUIRIES
