"""
State Machine - Sudha Hospital Conversational Bot
"""

import time
import logging
from typing import Dict, Any, Optional
from enum import Enum
from database import (
    get_conversation_state,
    set_conversation_state,
    reset_conversation_state,
    get_session as db_get_session,
    save_session as db_save_session,
    delete_session as db_delete_session,
)

logger = logging.getLogger(__name__)

SESSION_TIMEOUT = 1800


class ConversationState(Enum):
    MAIN_MENU = "MAIN_MENU"
    OPD_FLOW = "OPD_FLOW"
    ULTRASOUND_FLOW = "ULTRASOUND_FLOW"
    LAB_FLOW = "LAB_FLOW"
    PHARMACY_FLOW = "PHARMACY_FLOW"
    IPD_FLOW = "IPD_FLOW"
    POST_BOOKING = "POST_BOOKING"


class SubState(Enum):
    # Shared patient details
    ENTER_NAME = "ENTER_NAME"
    ENTER_AGE = "ENTER_AGE"
    SELECT_MARITAL = "SELECT_MARITAL"
    SELECT_CONCERN = "SELECT_CONCERN"

    # Pregnancy
    ASK_PREGNANT = "ASK_PREGNANT"
    SELECT_TRIMESTER = "SELECT_TRIMESTER"
    ENTER_LMP = "ENTER_LMP"

    # Menstrual / Menopause
    SELECT_SYMPTOMS = "SELECT_SYMPTOMS"
    ENTER_SYMPTOMS = "ENTER_SYMPTOMS"

    # Infertility
    ENTER_HUSBAND_NAME = "ENTER_HUSBAND_NAME"
    ENTER_HUSBAND_AGE = "ENTER_HUSBAND_AGE"
    ENTER_YEARS_MARRIED = "ENTER_YEARS_MARRIED"

    # Ultrasound
    SELECT_US_TYPE = "SELECT_US_TYPE"
    SELECT_SCAN = "SELECT_SCAN"
    ENTER_WEEKS = "ENTER_WEEKS"
    ENTER_DOCTOR_REF = "ENTER_DOCTOR_REF"

    # Lab
    SELECT_TEST = "SELECT_TEST"

    # Pharmacy
    SELECT_PHARMACY_HELP = "SELECT_PHARMACY_HELP"
    ENTER_MEDICINE_NAME = "ENTER_MEDICINE_NAME"
    WAIT_PRESCRIPTION_IMAGE = "WAIT_PRESCRIPTION_IMAGE"

    # IPD
    SELECT_ENQUIRY = "SELECT_ENQUIRY"
    SELECT_SURGERY_GROUP = "SELECT_SURGERY_GROUP"
    SELECT_SURGERY = "SELECT_SURGERY"
    ENTER_PHONE = "ENTER_PHONE"
    ENTER_HOSPITAL_ID = "ENTER_HOSPITAL_ID"

    # Booking
    SELECT_DATE = "SELECT_DATE"
    SELECT_TIME = "SELECT_TIME"
    CONFIRM = "CONFIRM"
    POST_CONFIRM = "POST_CONFIRM"
    CONFIRM_CANCEL = "CONFIRM_CANCEL"


class Session:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.current_state = ConversationState.MAIN_MENU.value
        self.sub_state: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.flow_token: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_state": self.current_state,
            "sub_state": self.sub_state,
            "context": self.context,
            "flow_token": self.flow_token,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        session = cls(data["user_id"])
        session.current_state = data.get("current_state", ConversationState.MAIN_MENU.value)
        session.sub_state = data.get("sub_state")
        session.context = data.get("context", {})
        session.flow_token = data.get("flow_token")
        session.created_at = data.get("created_at", time.time())
        session.updated_at = data.get("updated_at", time.time())
        return session

    def is_expired(self) -> bool:
        return (time.time() - self.updated_at) > SESSION_TIMEOUT

    def set_state(self, state: ConversationState, sub_state: Optional[SubState] = None):
        self.current_state = state.value
        self.sub_state = sub_state.value if sub_state else None
        self.updated_at = time.time()

    def set_sub_state(self, sub_state: SubState):
        self.sub_state = sub_state.value
        self.updated_at = time.time()

    def set_context(self, key: str, value: Any):
        self.context[key] = value
        self.updated_at = time.time()

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)

    def clear_context(self):
        self.context = {}
        self.updated_at = time.time()

    def reset(self):
        self.current_state = ConversationState.MAIN_MENU.value
        self.sub_state = None
        self.context = {}
        self.flow_token = None
        self.updated_at = time.time()


def get_session(user_id: str) -> Session:
    conv_state = get_conversation_state(user_id)

    if conv_state:
        session = Session(user_id)
        stored_mode = conv_state.get("mode", ConversationState.MAIN_MENU.value)
        # Map legacy Mallika modes if any old session exists
        mode_mapping = {
            "MENU": ConversationState.MAIN_MENU.value,
            "DIAGNOSTICS": ConversationState.LAB_FLOW.value,
            "DIAGNOSTICS_FLOW": ConversationState.LAB_FLOW.value,
            "ADMISSION": ConversationState.IPD_FLOW.value,
            "ADMISSION_FLOW": ConversationState.IPD_FLOW.value,
            "TEXT_APPOINTMENT": ConversationState.OPD_FLOW.value,
            "APPOINTMENT_FLOW": ConversationState.MAIN_MENU.value,
        }
        session.current_state = mode_mapping.get(stored_mode, stored_mode)
        session.sub_state = conv_state.get("sub_step")
        session.context = conv_state.get("context", {})
        session.flow_token = conv_state.get("flow_token")
        session.updated_at = conv_state.get("updated_at", time.time())

        if session.is_expired():
            logger.info(f"Session expired for {user_id[:6]}***, resetting to MAIN_MENU")
            session.reset()
            _save_session(session)
        return session

    legacy_session = db_get_session(user_id, SESSION_TIMEOUT)
    if legacy_session:
        session = Session(user_id)
        session.current_state = ConversationState.MAIN_MENU.value
        session.sub_state = legacy_session.get("step")
        session.context = legacy_session.get("data", {})
        session.updated_at = legacy_session.get("updated_at", time.time())
        _save_session(session)
        return session

    logger.info(f"Creating new session for {user_id[:6]}***")
    return Session(user_id)


def update_session(session: Session):
    _save_session(session)


def clear_session(user_id: str):
    logger.info(f"Clearing session for {user_id[:6]}***")
    reset_conversation_state(user_id)
    db_delete_session(user_id)


def _save_session(session: Session):
    set_conversation_state(
        user_id=session.user_id,
        mode=session.current_state,
        sub_step=session.sub_state,
        context=session.context,
        flow_token=session.flow_token,
    )

    type_map = {
        ConversationState.OPD_FLOW.value: "opd",
        ConversationState.ULTRASOUND_FLOW.value: "ultrasound",
        ConversationState.LAB_FLOW.value: "lab",
        ConversationState.PHARMACY_FLOW.value: "pharmacy",
        ConversationState.IPD_FLOW.value: "ipd",
        ConversationState.POST_BOOKING.value: "post_booking",
    }
    session_type = type_map.get(session.current_state)
    if session_type:
        db_save_session(
            user_id=session.user_id,
            step=session.sub_state or "start",
            data=session.context,
            session_type=session_type,
        )


def start_opd_flow(user_id: str) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.OPD_FLOW, SubState.SELECT_CONCERN)
    session.clear_context()
    session.set_context("department", "Out Patient Services")
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** -> OPD_FLOW")
    return session


def start_ultrasound_flow(user_id: str) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.ULTRASOUND_FLOW, SubState.SELECT_US_TYPE)
    session.clear_context()
    session.set_context("department", "Ultrasound Scanning")
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** -> ULTRASOUND_FLOW")
    return session


def start_lab_flow(user_id: str) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.LAB_FLOW, SubState.SELECT_TEST)
    session.clear_context()
    session.set_context("department", "Lab Services")
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** -> LAB_FLOW")
    return session


def start_pharmacy_flow(user_id: str) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.PHARMACY_FLOW, SubState.SELECT_PHARMACY_HELP)
    session.clear_context()
    session.set_context("department", "Pharmacy")
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** -> PHARMACY_FLOW")
    return session


def start_ipd_flow(user_id: str) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.IPD_FLOW, SubState.SELECT_ENQUIRY)
    session.clear_context()
    session.set_context("department", "In Patient Services")
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** -> IPD_FLOW")
    return session


def start_post_booking(user_id: str, booking_context: Dict[str, Any]) -> Session:
    session = get_session(user_id)
    session.set_state(ConversationState.POST_BOOKING, SubState.POST_CONFIRM)
    session.clear_context()
    for key, value in booking_context.items():
        session.set_context(key, value)
    _save_session(session)
    return session


def reset_to_main_menu(user_id: str) -> Session:
    session = get_session(user_id)
    session.reset()
    _save_session(session)
    logger.info(f"User {user_id[:6]}*** reset to MAIN_MENU")
    return session


def get_current_state(user_id: str) -> str:
    return get_session(user_id).current_state


def is_in_flow(user_id: str) -> bool:
    return get_current_state(user_id) != ConversationState.MAIN_MENU.value
