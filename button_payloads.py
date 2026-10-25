"""
Button Payloads - Sudha Hospital WhatsApp Bot
"""

from typing import Dict, Optional, Set


class MainMenuPayload:
    OPD = "MENU_OPD"
    ULTRASOUND = "MENU_ULTRASOUND"
    LAB = "MENU_LAB"
    LOCATION = "MENU_LOCATION"
    ABOUT = "MENU_ABOUT"
    IPD = "MENU_IPD"
    # Legacy (removed from menu)
    PHARMACY = "MENU_PHARMACY"


class OPDPayload:
    MARRIED = "OPD_MARRIED"
    UNMARRIED = "OPD_UNMARRIED"
    CONCERN_PREGNANCY = "OPD_CONCERN_PREGNANCY"
    CONCERN_MENSTRUAL = "OPD_CONCERN_MENSTRUAL"
    CONCERN_INFERTILITY = "OPD_CONCERN_INFERTILITY"
    CONCERN_MENOPAUSE = "OPD_CONCERN_MENOPAUSE"
    CONCERN_POST_DELIVERY = "OPD_CONCERN_POST_DELIVERY"
    CONCERN_CANCER = "OPD_CONCERN_CANCER"
    CONCERN_WELLNESS = "OPD_CONCERN_WELLNESS"
    PREGNANT_YES = "OPD_PREG_YES"
    PREGNANT_NO = "OPD_PREG_NO"
    TRIMESTER_1 = "OPD_TRIM_1"
    TRIMESTER_2 = "OPD_TRIM_2"
    TRIMESTER_3 = "OPD_TRIM_3"
    SYMPTOM_IRREGULAR = "OPD_SYM_IRREGULAR"
    SYMPTOM_HEAVY = "OPD_SYM_HEAVY"
    SYMPTOM_PAINFUL = "OPD_SYM_PAINFUL"
    SYMPTOM_MISSED = "OPD_SYM_MISSED"
    SYMPTOMS_DONE = "OPD_SYM_DONE"
    SYMPTOMS_SKIP = "OPD_SYM_SKIP"
    CONFIRM_YES = "OPD_CONFIRM_YES"
    CONFIRM_NO = "OPD_CONFIRM_NO"
    BACK_TO_MENU = "OPD_BACK_MENU"


class UltrasoundPayload:
    PREGNANT = "US_PREGNANT"
    NON_PREGNANT = "US_NON_PREGNANT"
    SCAN_LOCATION = "US_SCAN_LOCATION"
    SCAN_CARDIAC = "US_SCAN_CARDIAC"
    SCAN_NT = "US_SCAN_NT"
    SCAN_TIFFA = "US_SCAN_TIFFA"
    SCAN_GROWTH = "US_SCAN_GROWTH"
    SCAN_GROWTH_DOPPLER = "US_SCAN_GROWTH_DOPPLER"
    SCAN_PELVIS = "US_SCAN_PELVIS"
    SCAN_ABD_PELVIS = "US_SCAN_ABD_PELVIS"
    SCAN_FOLLICULAR = "US_SCAN_FOLLICULAR"
    SKIP_DOCTOR_REF = "US_SKIP_DOCTOR_REF"
    CONFIRM_YES = "US_CONFIRM_YES"
    CONFIRM_NO = "US_CONFIRM_NO"
    BACK_TO_MENU = "US_BACK_MENU"


class LabPayload:
    TEST_BLOOD = "LAB_TEST_BLOOD"
    TEST_THYROID = "LAB_TEST_THYROID"
    TEST_SUGAR = "LAB_TEST_SUGAR"
    TEST_URINE = "LAB_TEST_URINE"
    TEST_CBC = "LAB_TEST_CBC"
    TEST_OTHERS = "LAB_TEST_OTHERS"
    SKIP_DOCTOR_REF = "LAB_SKIP_DOCTOR_REF"
    CONFIRM_YES = "LAB_CONFIRM_YES"
    CONFIRM_NO = "LAB_CONFIRM_NO"
    BACK_TO_MENU = "LAB_BACK_MENU"


class PharmacyPayload:
    AVAILABILITY = "PHARM_AVAILABILITY"
    UPLOAD = "PHARM_UPLOAD"
    CONTACT = "PHARM_CONTACT"
    BACK_TO_MENU = "PHARM_BACK_MENU"


class IPDPayload:
    ADMISSION = "IPD_ADMISSION"
    RECEPTION = "IPD_RECEPTION"
    SURG_GROUP_OBSTETRIC = "IPD_SURG_GRP_OBS"
    SURG_GROUP_GYNE = "IPD_SURG_GRP_GYN"
    SURG_CAESAREAN = "IPD_SURG_CS"
    SURG_CERCLAGE = "IPD_SURG_CERCLAGE"
    SURG_DNC = "IPD_SURG_DNC"
    SURG_ENDOMETRIAL = "IPD_SURG_ENDO"
    SURG_LAP_TUBE = "IPD_SURG_LAP_TUBE"
    SURG_OPEN_TUBE = "IPD_SURG_OPEN_TUBE"
    SURG_LAP_HYST = "IPD_SURG_LAP_HYST"
    SURG_OPEN_HYST = "IPD_SURG_OPEN_HYST"
    SURG_DIAG_HYSTERO = "IPD_SURG_DIAG_HYST"
    SURG_DIAG_LAP = "IPD_SURG_DIAG_LAP"
    SURG_LAP_CYST = "IPD_SURG_LAP_CYST"
    SURG_BARTHOLIN = "IPD_SURG_BARTHOLIN"
    # Legacy (removed from menu)
    ROOM = "IPD_ROOM"
    INSURANCE = "IPD_INSURANCE"
    BILLING = "IPD_BILLING"
    SKIP_HOSPITAL_ID = "IPD_SKIP_HOSPITAL_ID"
    BACK_TO_MENU = "IPD_BACK_MENU"


class BookingPayload:
    MODIFY = "BOOK_MODIFY"
    CANCEL = "BOOK_CANCEL"
    CONFIRM_CANCEL_YES = "BOOK_CANCEL_YES"
    CONFIRM_CANCEL_NO = "BOOK_CANCEL_NO"


class GlobalPayload:
    MAIN_MENU = "GLOBAL_MAIN_MENU"
    CANCEL = "GLOBAL_CANCEL"
    HELP = "GLOBAL_HELP"


OPD_CONCERN_MAP = {
    OPDPayload.CONCERN_PREGNANCY: {"id": "pregnancy", "name": "Pregnancy"},
    OPDPayload.CONCERN_MENSTRUAL: {"id": "menstrual", "name": "Menstrual Problems"},
    OPDPayload.CONCERN_INFERTILITY: {"id": "infertility", "name": "Infertility"},
    OPDPayload.CONCERN_MENOPAUSE: {"id": "menopause", "name": "Menopause"},
    OPDPayload.CONCERN_POST_DELIVERY: {"id": "post_delivery", "name": "Post Delivery Care"},
    OPDPayload.CONCERN_CANCER: {"id": "cancer_screening", "name": "Cancer Screening"},
    OPDPayload.CONCERN_WELLNESS: {"id": "wellness", "name": "General Wellness Checkup"},
}

OPD_TRIMESTER_MAP = {
    OPDPayload.TRIMESTER_1: "First Trimester",
    OPDPayload.TRIMESTER_2: "Second Trimester",
    OPDPayload.TRIMESTER_3: "Third Trimester",
}

OPD_SYMPTOM_MAP = {
    OPDPayload.SYMPTOM_IRREGULAR: "Irregular periods",
    OPDPayload.SYMPTOM_HEAVY: "Heavy bleeding",
    OPDPayload.SYMPTOM_PAINFUL: "Painful periods",
    OPDPayload.SYMPTOM_MISSED: "Missed periods",
}

US_PREGNANT_SCAN_MAP = {
    UltrasoundPayload.SCAN_LOCATION: {"id": "location", "name": "Location of Pregnancy Scan"},
    UltrasoundPayload.SCAN_CARDIAC: {"id": "cardiac", "name": "Cardiac Activity Scan"},
    UltrasoundPayload.SCAN_NT: {"id": "nt", "name": "NT Scan"},
    UltrasoundPayload.SCAN_TIFFA: {"id": "tiffa", "name": "TIFFA Scan"},
    UltrasoundPayload.SCAN_GROWTH: {"id": "growth", "name": "Growth Scan"},
    UltrasoundPayload.SCAN_GROWTH_DOPPLER: {"id": "growth_doppler", "name": "Growth Doppler"},
}

US_NON_PREGNANT_SCAN_MAP = {
    UltrasoundPayload.SCAN_PELVIS: {"id": "pelvis", "name": "Pelvis Scan"},
    UltrasoundPayload.SCAN_ABD_PELVIS: {"id": "abd_pelvis", "name": "Whole Abdomen + Pelvis"},
    UltrasoundPayload.SCAN_FOLLICULAR: {"id": "follicular", "name": "Follicular Study"},
}

LAB_TEST_MAP = {
    LabPayload.TEST_BLOOD: {"id": "blood", "name": "Blood Test"},
    LabPayload.TEST_THYROID: {"id": "thyroid", "name": "Thyroid"},
    LabPayload.TEST_SUGAR: {"id": "sugar", "name": "Sugar"},
    LabPayload.TEST_URINE: {"id": "urine", "name": "Urine Test"},
    LabPayload.TEST_CBC: {"id": "cbc", "name": "CBC"},
    LabPayload.TEST_OTHERS: {"id": "others", "name": "Others"},
}

IPD_MENU_MAP = {
    IPDPayload.ADMISSION: {"id": "admission", "name": "Admission / Surgery"},
    IPDPayload.RECEPTION: {"id": "reception", "name": "Contact Reception"},
}

IPD_SURGERY_GROUP_MAP = {
    IPDPayload.SURG_GROUP_OBSTETRIC: {"id": "obstetric", "name": "Obstetric"},
    IPDPayload.SURG_GROUP_GYNE: {"id": "gynecological", "name": "Gynecological"},
}

IPD_OBSTETRIC_SURGERY_MAP = {
    IPDPayload.SURG_CAESAREAN: {"id": "caesarean", "name": "Caesarean section"},
    IPDPayload.SURG_CERCLAGE: {"id": "cerclage", "name": "Cerclage"},
    IPDPayload.SURG_DNC: {"id": "dnc", "name": "D and C"},
}

IPD_GYNE_SURGERY_MAP = {
    IPDPayload.SURG_ENDOMETRIAL: {"id": "endometrial", "name": "Endometrial Biopsy"},
    IPDPayload.SURG_LAP_TUBE: {"id": "lap_tubectomy", "name": "Lap tubectomy"},
    IPDPayload.SURG_OPEN_TUBE: {"id": "open_tubectomy", "name": "Open tubectomy"},
    IPDPayload.SURG_LAP_HYST: {"id": "lap_hysterectomy", "name": "Lap hysterectomy"},
    IPDPayload.SURG_OPEN_HYST: {"id": "open_hysterectomy", "name": "Open hysterectomy"},
    IPDPayload.SURG_DIAG_HYSTERO: {"id": "diag_hysteroscopy", "name": "Diagnostic Hysteroscopy"},
    IPDPayload.SURG_DIAG_LAP: {"id": "diag_laparoscopy", "name": "Diagnostic Laparoscopy"},
    IPDPayload.SURG_LAP_CYST: {"id": "lap_cystectomy", "name": "Lap cystectomy"},
    IPDPayload.SURG_BARTHOLIN: {"id": "bartholin", "name": "Bartholin abscess drain"},
}

IPD_SURGERY_MAP = {**IPD_OBSTETRIC_SURGERY_MAP, **IPD_GYNE_SURGERY_MAP}

# Back-compat alias used by older imports
IPD_ENQUIRY_MAP = IPD_MENU_MAP

GLOBAL_PAYLOADS: Set[str] = {
    GlobalPayload.MAIN_MENU,
    GlobalPayload.CANCEL,
    GlobalPayload.HELP,
}

VALID_PAYLOADS_BY_STATE: Dict[str, Set[str]] = {
    "MAIN_MENU": {
        MainMenuPayload.OPD,
        MainMenuPayload.ULTRASOUND,
        MainMenuPayload.LAB,
        MainMenuPayload.LOCATION,
        MainMenuPayload.ABOUT,
        MainMenuPayload.IPD,
        MainMenuPayload.PHARMACY,
        GlobalPayload.HELP,
    },
    "OPD_FLOW": {
        OPDPayload.MARRIED,
        OPDPayload.UNMARRIED,
        *OPD_CONCERN_MAP.keys(),
        OPDPayload.PREGNANT_YES,
        OPDPayload.PREGNANT_NO,
        OPDPayload.TRIMESTER_1,
        OPDPayload.TRIMESTER_2,
        OPDPayload.TRIMESTER_3,
        OPDPayload.SYMPTOM_IRREGULAR,
        OPDPayload.SYMPTOM_HEAVY,
        OPDPayload.SYMPTOM_PAINFUL,
        OPDPayload.SYMPTOM_MISSED,
        OPDPayload.SYMPTOMS_DONE,
        OPDPayload.SYMPTOMS_SKIP,
        OPDPayload.CONFIRM_YES,
        OPDPayload.CONFIRM_NO,
        OPDPayload.BACK_TO_MENU,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
    "ULTRASOUND_FLOW": {
        UltrasoundPayload.PREGNANT,
        UltrasoundPayload.NON_PREGNANT,
        *US_PREGNANT_SCAN_MAP.keys(),
        *US_NON_PREGNANT_SCAN_MAP.keys(),
        UltrasoundPayload.SKIP_DOCTOR_REF,
        UltrasoundPayload.CONFIRM_YES,
        UltrasoundPayload.CONFIRM_NO,
        UltrasoundPayload.BACK_TO_MENU,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
    "LAB_FLOW": {
        *LAB_TEST_MAP.keys(),
        LabPayload.SKIP_DOCTOR_REF,
        LabPayload.CONFIRM_YES,
        LabPayload.CONFIRM_NO,
        LabPayload.BACK_TO_MENU,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
    "PHARMACY_FLOW": {
        PharmacyPayload.AVAILABILITY,
        PharmacyPayload.UPLOAD,
        PharmacyPayload.CONTACT,
        PharmacyPayload.BACK_TO_MENU,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
    "IPD_FLOW": {
        *IPD_MENU_MAP.keys(),
        *IPD_SURGERY_GROUP_MAP.keys(),
        *IPD_SURGERY_MAP.keys(),
        IPDPayload.ROOM,
        IPDPayload.INSURANCE,
        IPDPayload.BILLING,
        IPDPayload.SKIP_HOSPITAL_ID,
        IPDPayload.BACK_TO_MENU,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
    "POST_BOOKING": {
        BookingPayload.MODIFY,
        BookingPayload.CANCEL,
        BookingPayload.CONFIRM_CANCEL_YES,
        BookingPayload.CONFIRM_CANCEL_NO,
        GlobalPayload.MAIN_MENU,
        GlobalPayload.CANCEL,
    },
}


def is_valid_payload(payload: str, current_state: str) -> bool:
    if payload in GLOBAL_PAYLOADS:
        return True

    if payload.startswith("DATE_") or payload.startswith("TIME_"):
        return current_state in {
            "OPD_FLOW",
            "ULTRASOUND_FLOW",
            "LAB_FLOW",
            "POST_BOOKING",
        }

    valid_payloads = VALID_PAYLOADS_BY_STATE.get(current_state, set())
    return payload in valid_payloads


def is_button_payload(message: str) -> bool:
    if not message:
        return False
    return message.startswith((
        "MENU_", "OPD_", "US_", "LAB_", "PHARM_", "IPD_", "BOOK_", "GLOBAL_", "DATE_", "TIME_"
    ))


def is_numeric_input(message: str) -> bool:
    cleaned = message.strip()
    if cleaned.isdigit() and len(cleaned) <= 2:
        return True
    if len(cleaned) >= 2 and cleaned[0].isdigit() and cleaned[1] in ".):":
        return True
    return False


def get_main_menu_payload_from_text(message: str) -> Optional[str]:
    message_lower = message.lower().strip()
    text_to_payload = {
        "1": MainMenuPayload.OPD,
        "2": MainMenuPayload.ULTRASOUND,
        "3": MainMenuPayload.LAB,
        "4": MainMenuPayload.LOCATION,
        "5": MainMenuPayload.ABOUT,
        "6": MainMenuPayload.IPD,
        "opd": MainMenuPayload.OPD,
        "out patient": MainMenuPayload.OPD,
        "outpatient": MainMenuPayload.OPD,
        "ultrasound": MainMenuPayload.ULTRASOUND,
        "scan": MainMenuPayload.ULTRASOUND,
        "lab": MainMenuPayload.LAB,
        "laboratory": MainMenuPayload.LAB,
        "location": MainMenuPayload.LOCATION,
        "address": MainMenuPayload.LOCATION,
        "directions": MainMenuPayload.LOCATION,
        "about": MainMenuPayload.ABOUT,
        "website": MainMenuPayload.ABOUT,
        "ipd": MainMenuPayload.IPD,
        "admission": MainMenuPayload.IPD,
        "in patient": MainMenuPayload.IPD,
        "inpatient": MainMenuPayload.IPD,
        "surgery": MainMenuPayload.IPD,
        "menu": GlobalPayload.MAIN_MENU,
        "main menu": GlobalPayload.MAIN_MENU,
        "home": GlobalPayload.MAIN_MENU,
        "start": GlobalPayload.MAIN_MENU,
        "hi": GlobalPayload.MAIN_MENU,
        "hello": GlobalPayload.MAIN_MENU,
        "hey": GlobalPayload.MAIN_MENU,
        "cancel": GlobalPayload.CANCEL,
        "stop": GlobalPayload.CANCEL,
        "exit": GlobalPayload.CANCEL,
        "help": GlobalPayload.HELP,
    }
    return text_to_payload.get(message_lower)
