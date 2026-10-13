"""
Session Manager
Database-backed session management for booking, diagnostics, and admission flows.
Supports multiple session types:
- appointment: Doctor appointment booking
- diagnostics: Diagnostic test booking
- admission: Hospital admission request
"""

import time
from typing import Optional, Any
from database import (
    get_session as db_get_session,
    save_session as db_save_session,
    delete_session as db_delete_session,
    session_exists as db_session_exists
)

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


class BookingSession:
    """Represents an active booking session with database backing."""
    
    # Different step flows for different session types
    APPOINTMENT_STEPS = ['doctor', 'date', 'time', 'patient_name', 'phone', 'confirm']
    DIAGNOSTICS_STEPS = ['test', 'patient_name', 'date', 'time', 'phone', 'confirm']
    ADMISSION_STEPS = ['admission_type', 'patient_name', 'age', 'sex', 'confirm']
    
    def __init__(self, user_id: str, session_type: str = 'appointment'):
        self.user_id = user_id
        self.session_type = session_type
        
        # Set appropriate steps and initial data based on session type
        if session_type == 'diagnostics':
            self.step = 'test'
            self.data = {
                'test_type': None,
                'test_name': None,
                'patient_name': None,
                'date': None,
                'time': None,
                'phone': None
            }
        elif session_type == 'admission':
            self.step = 'admission_type'
            self.data = {
                'admission_type': None,
                'patient_name': None,
                'age': None,
                'sex': None,
                'is_walkin': False
            }
        else:  # appointment
            self.step = 'doctor'
            self.data = {
                'doctor_id': None,
                'doctor_name': None,
                'doctor_specialty': None,
                'date': None,
                'time': None,
                'patient_name': None,
                'phone': None
            }
        
        self.created_at = time.time()
        self.updated_at = time.time()
    
    def get_steps(self) -> list:
        """Get steps for current session type."""
        if self.session_type == 'diagnostics':
            return self.DIAGNOSTICS_STEPS
        elif self.session_type == 'admission':
            return self.ADMISSION_STEPS
        return self.APPOINTMENT_STEPS
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'step': self.step,
            'data': self.data,
            'session_type': self.session_type,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BookingSession':
        session_type = data.get('session_type', 'appointment')
        session = cls(data['user_id'], session_type)
        session.step = data['step']
        session.data = data['data']
        session.created_at = data['created_at']
        session.updated_at = data['updated_at']
        return session
    
    def is_expired(self) -> bool:
        return (time.time() - self.updated_at) > SESSION_TIMEOUT
    
    def next_step(self) -> Optional[str]:
        """Move to next step in booking flow."""
        steps = self.get_steps()
        try:
            current_index = steps.index(self.step)
            if current_index < len(steps) - 1:
                self.step = steps[current_index + 1]
                self.updated_at = time.time()
                return self.step
        except ValueError:
            pass
        return None
    
    def set_value(self, key: str, value: Any):
        """Set a value in session data."""
        self.data[key] = value
        self.updated_at = time.time()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a value from session data."""
        return self.data.get(key, default)
    
    def save(self):
        """Save session to database."""
        db_save_session(self.user_id, self.step, self.data, self.session_type)


def get_session(user_id: str) -> Optional[BookingSession]:
    """Get active booking session for user from database."""
    session_data = db_get_session(user_id, SESSION_TIMEOUT)
    
    if session_data:
        return BookingSession.from_dict(session_data)
    
    return None


def get_session_type(user_id: str) -> Optional[str]:
    """Get the session type for a user (appointment, diagnostics, admission)."""
    session_data = db_get_session(user_id, SESSION_TIMEOUT)
    if session_data:
        return session_data.get('session_type', 'appointment')
    return None


def create_session(user_id: str, session_type: str = 'appointment') -> BookingSession:
    """Create new booking session and save to database."""
    session = BookingSession(user_id, session_type)
    session.save()
    return session


def update_session(session: BookingSession):
    """Update session in database."""
    session.save()


def delete_session(user_id: str):
    """Delete booking session from database."""
    db_delete_session(user_id)


def has_active_session(user_id: str) -> bool:
    """Check if user has active booking session."""
    return db_session_exists(user_id, SESSION_TIMEOUT)
