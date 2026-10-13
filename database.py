"""
Database Module - Production Ready
SQLite database for Sudha Hospital WhatsApp Bot

Tables:
- appointments: Service appointments
- diagnostics: Legacy diagnostic bookings
- admissions: Legacy admission requests
- enquiries: IPD / staff enquiries
- pharmacy_prescriptions: Uploaded prescriptions
- staff_notifications: Staff alert queue
- patients: CRM patient profiles
- interactions: Chat history/timeline
- conversation_state: User session state
- sessions: Legacy session storage
- ai_interactions: AI response logs
"""

import sqlite3
import time
import json
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_FILE = 'clinic_bot.db'


def _normalize_appointment_date(date_value: Optional[str]) -> Optional[str]:
    """Normalize date strings to YYYY-MM-DD for reliable querying."""
    if not date_value:
        return date_value

    date_text = str(date_value).strip()
    if not date_text:
        return date_text

    formats = [
        "%Y-%m-%d",
        "%a, %d %b %Y",
        "%d %b %Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return date_text


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _add_column_if_not_exists(cursor, table: str, column: str, column_def: str):
    """Safely add a column to a table if it doesn't exist."""
    try:
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
            logger.info(f"Added column {column} to {table}")
        except sqlite3.OperationalError as e:
            logger.debug(f"Column {column} might already exist: {e}")


def _create_index_if_column_exists(cursor, index_name: str, table: str, column: str):
    """Create an index only if the column exists."""
    try:
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
        cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})')
    except sqlite3.OperationalError:
        logger.debug(f"Skipping index {index_name} - column {column} doesn't exist yet")


def init_database():
    """Initialize database with all required tables for production."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ============ APPOINTMENTS TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                department TEXT,
                department_name TEXT,
                doctor TEXT,
                date TEXT,
                time TEXT,
                status TEXT DEFAULT 'confirmed',
                clinic_id TEXT DEFAULT 'default',
                service_type TEXT DEFAULT 'appointment',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Add new columns to existing tables (safe for both new and existing DBs)
        _add_column_if_not_exists(cursor, 'appointments', 'phone', "TEXT")
        _add_column_if_not_exists(cursor, 'appointments', 'source', "TEXT DEFAULT 'whatsapp'")
        _add_column_if_not_exists(cursor, 'appointments', 'notes', "TEXT")
        _add_column_if_not_exists(cursor, 'appointments', 'updated_at', "REAL")
        _add_column_if_not_exists(cursor, 'appointments', 'patient_identifier', "TEXT")
        _add_column_if_not_exists(cursor, 'appointments', 'cancel_reason', "TEXT")
        _add_column_if_not_exists(cursor, 'appointments', 'cancelled_by', "TEXT")
        _add_column_if_not_exists(cursor, 'appointments', 'cancelled_at', "REAL")
        
        # Index for faster lookups (only if columns exist)
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)')
        _create_index_if_column_exists(cursor, 'idx_appointments_phone', 'appointments', 'phone')
        _create_index_if_column_exists(cursor, 'idx_appointments_patient_identifier', 'appointments', 'patient_identifier')
        
        
        # ============ DIAGNOSTICS TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnostics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                test_type TEXT NOT NULL,
                date TEXT,
                time TEXT,
                status TEXT DEFAULT 'confirmed',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Add new columns to existing diagnostics table
        _add_column_if_not_exists(cursor, 'diagnostics', 'phone', "TEXT")
        _add_column_if_not_exists(cursor, 'diagnostics', 'clinic_id', "TEXT DEFAULT 'default'")
        _add_column_if_not_exists(cursor, 'diagnostics', 'source', "TEXT DEFAULT 'whatsapp'")
        _add_column_if_not_exists(cursor, 'diagnostics', 'notes', "TEXT")
        _add_column_if_not_exists(cursor, 'diagnostics', 'updated_at', "REAL")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diagnostics_user ON diagnostics(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diagnostics_date ON diagnostics(date)')
        _create_index_if_column_exists(cursor, 'idx_diagnostics_phone', 'diagnostics', 'phone')
        
        # ============ ADMISSIONS TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                age TEXT,
                sex TEXT,
                admission_type TEXT,
                is_walkin INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Add new columns to existing admissions table
        _add_column_if_not_exists(cursor, 'admissions', 'phone', "TEXT")
        _add_column_if_not_exists(cursor, 'admissions', 'preferred_date', "TEXT")
        _add_column_if_not_exists(cursor, 'admissions', 'clinic_id', "TEXT DEFAULT 'default'")
        _add_column_if_not_exists(cursor, 'admissions', 'source', "TEXT DEFAULT 'whatsapp'")
        _add_column_if_not_exists(cursor, 'admissions', 'notes', "TEXT")
        _add_column_if_not_exists(cursor, 'admissions', 'updated_at', "REAL")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admissions_user ON admissions(user_id)')
        _create_index_if_column_exists(cursor, 'idx_admissions_date', 'admissions', 'preferred_date')
        _create_index_if_column_exists(cursor, 'idx_admissions_phone', 'admissions', 'phone')
        
        # ============ PATIENTS (CRM) TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL,
                platform TEXT NOT NULL DEFAULT 'whatsapp',
                name TEXT,
                phone TEXT,
                email TEXT,
                total_bookings INTEGER DEFAULT 0,
                notes TEXT,
                first_touch REAL DEFAULT (strftime('%s', 'now')),
                last_touch REAL DEFAULT (strftime('%s', 'now')),
                UNIQUE(external_id, platform)
            )
        ''')
        
        # Add new columns to existing patients table
        _add_column_if_not_exists(cursor, 'patients', 'total_appointments', "INTEGER DEFAULT 0")
        _add_column_if_not_exists(cursor, 'patients', 'total_diagnostics', "INTEGER DEFAULT 0")
        _add_column_if_not_exists(cursor, 'patients', 'total_admissions', "INTEGER DEFAULT 0")
        _add_column_if_not_exists(cursor, 'patients', 'tags', "TEXT")
        _add_column_if_not_exists(cursor, 'patients', 'hospital_patient_id', "TEXT")
        _add_column_if_not_exists(cursor, 'patients', 'automation_paused', "INTEGER DEFAULT 0")
        
        _create_index_if_column_exists(cursor, 'idx_patients_phone', 'patients', 'phone')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_external ON patients(external_id)')
        _create_index_if_column_exists(cursor, 'idx_patients_hospital_id', 'patients', 'hospital_patient_id')
        
        # ============ INTERACTIONS TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                direction TEXT,
                platform TEXT DEFAULT 'whatsapp',
                message TEXT,
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        ''')
        
        # Add new columns to existing interactions table
        _add_column_if_not_exists(cursor, 'interactions', 'user_id', "TEXT")
        _add_column_if_not_exists(cursor, 'interactions', 'message_type', "TEXT DEFAULT 'text'")
        _add_column_if_not_exists(cursor, 'interactions', 'payload', "TEXT")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_patient ON interactions(patient_id)')
        _create_index_if_column_exists(cursor, 'idx_interactions_user', 'interactions', 'user_id')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_time ON interactions(timestamp)')
        
        # ============ CONVERSATION STATE TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                mode TEXT NOT NULL DEFAULT 'MAIN_MENU',
                sub_step TEXT,
                context TEXT,
                flow_token TEXT,
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_state_user ON conversation_state(user_id)')
        
        # ============ SESSIONS TABLE (Legacy) ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                step TEXT NOT NULL,
                data TEXT,
                session_type TEXT DEFAULT 'appointment',
                created_at REAL DEFAULT (strftime('%s', 'now')),
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # ============ AI INTERACTIONS LOG ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_message TEXT,
                ai_response TEXT,
                model TEXT DEFAULT 'gemini',
                timestamp REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # ============ FLOW PERSISTENCE TABLE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flow_persistence (
                flow_token TEXT PRIMARY KEY,
                flow_data TEXT NOT NULL,
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_flow_token ON flow_persistence(flow_token)')

        # ============ CRM AUTHENTICATION TABLES ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crm_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'staff',
                created_at REAL DEFAULT (strftime('%s', 'now')),
                last_login REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crm_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES crm_users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_user ON crm_sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_expiry ON crm_sessions(expires_at)')

        # ============ SUDHA: ENQUIRIES ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enquiry_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                patient_name TEXT,
                phone TEXT,
                hospital_id TEXT,
                enquiry_type TEXT,
                department TEXT DEFAULT 'In Patient Services',
                status TEXT DEFAULT 'open',
                notes TEXT,
                source TEXT DEFAULT 'whatsapp',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_enquiries_user ON enquiries(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_enquiries_status ON enquiries(status)')

        # ============ SUDHA: PHARMACY PRESCRIPTIONS ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pharmacy_prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                phone TEXT,
                media_id TEXT,
                media_url TEXT,
                local_path TEXT,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rx_user ON pharmacy_prescriptions(user_id)')

        # ============ SUDHA: STAFF NOTIFICATIONS ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS staff_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                category TEXT,
                reference_id TEXT,
                user_id TEXT,
                payload TEXT,
                is_read INTEGER DEFAULT 0,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_staff_notif_read ON staff_notifications(is_read)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_staff_notif_time ON staff_notifications(created_at)')

        # ============ WEBHOOK DEDUPE ============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_webhook_messages (
                message_id TEXT PRIMARY KEY,
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')

        conn.commit()
        logger.info("Database initialized successfully - Sudha Hospital Ready")


def was_webhook_message_processed(message_id: str) -> bool:
    if not message_id:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM processed_webhook_messages WHERE message_id = ? LIMIT 1',
                (message_id,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.debug(f"was_webhook_message_processed error: {e}")
        return False


def mark_webhook_message_processed(message_id: str) -> bool:
    if not message_id:
        return False
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO processed_webhook_messages (message_id) VALUES (?)',
                (message_id,),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.debug(f"mark_webhook_message_processed error: {e}")
        return False


# ============================================================================
# APPOINTMENT FUNCTIONS
# ============================================================================

def save_appointment(
    booking_id: str,
    user_id: str,
    patient_name: str,
    department: str = None,
    department_name: str = None,
    doctor: str = None,
    date: str = None,
    time_slot: str = None,
    clinic_id: str = 'default',
    service_type: str = 'appointment',
    phone: str = None,
    source: str = 'whatsapp',
    patient_identifier: str = None,
    notes: str = None,
) -> bool:
    """Save a new appointment to database."""
    try:
        normalized_date = _normalize_appointment_date(date)

        # Auto-detect source from user_id if it's the default 'whatsapp'
        if source == 'whatsapp':
            if user_id.startswith('instagram_'):
                source = 'instagram'
            elif user_id.startswith('facebook_'):
                source = 'facebook'

        # Use user_id as phone if not provided
        if not phone:
            phone = user_id
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO appointments 
                (booking_id, user_id, patient_name, phone, department, department_name, 
                 doctor, date, time, clinic_id, service_type, source, patient_identifier, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (booking_id, user_id, patient_name, phone, department, department_name,
                  doctor, normalized_date, time_slot, clinic_id, service_type, source,
                  patient_identifier, notes))

            # Keep CRM profile linked with hospital-side patient ID when provided.
            if patient_identifier and str(patient_identifier).strip():
                cleaned_patient_id = str(patient_identifier).strip()
                cursor.execute('''
                    UPDATE patients
                    SET hospital_patient_id = ?, last_touch = ?
                    WHERE (external_id = ? OR phone = ?)
                      AND (hospital_patient_id IS NULL OR TRIM(hospital_patient_id) = '' OR hospital_patient_id = ?)
                ''', (cleaned_patient_id, time.time(), user_id, phone, cleaned_patient_id))
            conn.commit()
            
            # Update CRM patient booking count
            _increment_patient_appointments(user_id)
            
            logger.info(f"Appointment saved: {booking_id} for {patient_name} via {source}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Appointment {booking_id} already exists")
        return False
    except Exception as e:
        logger.error(f"Error saving appointment: {e}")
        return False


def update_appointment_slot(booking_id: str, date: str = None, time_slot: str = None) -> bool:
    """Update date/time for an existing appointment."""
    try:
        normalized_date = _normalize_appointment_date(date) if date else None
        with get_connection() as conn:
            cursor = conn.cursor()
            if normalized_date and time_slot:
                cursor.execute(
                    '''UPDATE appointments SET date = ?, time = ?, updated_at = ?, status = 'confirmed'
                       WHERE booking_id = ?''',
                    (normalized_date, time_slot, time.time(), booking_id),
                )
            elif normalized_date:
                cursor.execute(
                    '''UPDATE appointments SET date = ?, updated_at = ? WHERE booking_id = ?''',
                    (normalized_date, time.time(), booking_id),
                )
            elif time_slot:
                cursor.execute(
                    '''UPDATE appointments SET time = ?, updated_at = ? WHERE booking_id = ?''',
                    (time_slot, time.time(), booking_id),
                )
            else:
                return False
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating appointment slot: {e}")
        return False


def notify_staff(
    title: str,
    message: str,
    category: str = "general",
    reference_id: str = None,
    user_id: str = None,
    payload: Dict[str, Any] = None,
) -> bool:
    """Store a staff notification for dashboard / ops follow-up."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO staff_notifications
                   (title, message, category, reference_id, user_id, payload)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    title,
                    message,
                    category,
                    reference_id,
                    user_id,
                    json.dumps(payload or {}, ensure_ascii=True),
                ),
            )
            conn.commit()
            logger.info(f"Staff notified: {category} - {title}")
            return True
    except Exception as e:
        logger.error(f"Error creating staff notification: {e}")
        return False


def save_enquiry(
    enquiry_id: str,
    user_id: str,
    patient_name: str = None,
    phone: str = None,
    hospital_id: str = None,
    enquiry_type: str = None,
    department: str = "In Patient Services",
    notes: str = None,
    source: str = "whatsapp",
) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO enquiries
                   (enquiry_id, user_id, patient_name, phone, hospital_id, enquiry_type,
                    department, notes, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    enquiry_id,
                    user_id,
                    patient_name,
                    phone or user_id,
                    hospital_id,
                    enquiry_type,
                    department,
                    notes,
                    source,
                ),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving enquiry: {e}")
        return False


def save_prescription(
    request_id: str,
    user_id: str,
    media_id: str = None,
    media_url: str = None,
    local_path: str = None,
    notes: str = None,
) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO pharmacy_prescriptions
                   (request_id, user_id, phone, media_id, media_url, local_path, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (request_id, user_id, user_id, media_id, media_url, local_path, notes),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving prescription: {e}")
        return False


def get_all_enquiries(status: str = None, limit: int = 100) -> List[Dict]:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM enquiries WHERE 1=1'
            params: List[Any] = []
            if status:
                query += ' AND status = ?'
                params.append(status)
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting enquiries: {e}")
        return []


def update_enquiry_status(enquiry_id: str, status: str) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE enquiries SET status = ? WHERE enquiry_id = ?',
                (status, enquiry_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating enquiry: {e}")
        return False


def get_all_prescriptions(status: str = None, limit: int = 100) -> List[Dict]:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM pharmacy_prescriptions WHERE 1=1'
            params: List[Any] = []
            if status:
                query += ' AND status = ?'
                params.append(status)
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting prescriptions: {e}")
        return []


def update_prescription_status(request_id: str, status: str) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE pharmacy_prescriptions SET status = ? WHERE request_id = ?',
                (status, request_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating prescription: {e}")
        return False


def get_staff_notifications(unread_only: bool = False, limit: int = 100) -> List[Dict]:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM staff_notifications WHERE 1=1'
            params: List[Any] = []
            if unread_only:
                query += ' AND is_read = 0'
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, params)
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get('payload'):
                    try:
                        item['payload'] = json.loads(item['payload'])
                    except Exception:
                        pass
                rows.append(item)
            return rows
    except Exception as e:
        logger.error(f"Error getting staff notifications: {e}")
        return []


def mark_staff_notification_read(notification_id: int) -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE staff_notifications SET is_read = 1 WHERE id = ?',
                (notification_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        return False


def mark_all_staff_notifications_read() -> bool:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE staff_notifications SET is_read = 1 WHERE is_read = 0')
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error marking all notifications read: {e}")
        return False


def get_staff_request_feed(limit: int = 100) -> List[Dict]:
    """Unified staff inbox: appointments + enquiries + pharmacy + notifications."""
    feed: List[Dict] = []
    try:
        for a in get_all_appointments(limit=limit):
            feed.append({
                'kind': 'appointment',
                'id': a.get('booking_id'),
                'title': 'Appointment',
                'subtitle': a.get('service_type') or a.get('department_name') or a.get('doctor') or 'Booking',
                'patient_name': a.get('patient_name'),
                'phone': a.get('phone') or a.get('user_id'),
                'status': a.get('status'),
                'date': a.get('date'),
                'time': a.get('time'),
                'notes': a.get('notes'),
                'created_at': a.get('created_at') or 0,
                'raw': a,
            })
        for e in get_all_enquiries(limit=limit):
            feed.append({
                'kind': 'enquiry',
                'id': e.get('enquiry_id'),
                'title': 'IPD Enquiry',
                'subtitle': e.get('enquiry_type') or 'Enquiry',
                'patient_name': e.get('patient_name'),
                'phone': e.get('phone') or e.get('user_id'),
                'status': e.get('status'),
                'date': None,
                'time': None,
                'notes': e.get('notes'),
                'created_at': e.get('created_at') or 0,
                'raw': e,
            })
        for p in get_all_prescriptions(limit=limit):
            feed.append({
                'kind': 'pharmacy',
                'id': p.get('request_id'),
                'title': 'Pharmacy',
                'subtitle': p.get('notes') or 'Prescription / request',
                'patient_name': p.get('phone') or p.get('user_id'),
                'phone': p.get('phone') or p.get('user_id'),
                'status': p.get('status'),
                'date': None,
                'time': None,
                'notes': p.get('media_id'),
                'created_at': p.get('created_at') or 0,
                'raw': p,
            })
        for n in get_staff_notifications(limit=limit):
            feed.append({
                'kind': 'notification',
                'id': str(n.get('id')),
                'title': n.get('title') or 'Staff alert',
                'subtitle': n.get('message'),
                'patient_name': None,
                'phone': n.get('user_id'),
                'status': 'unread' if not n.get('is_read') else 'read',
                'date': None,
                'time': None,
                'notes': n.get('category'),
                'created_at': n.get('created_at') or 0,
                'raw': n,
            })
        feed.sort(key=lambda x: float(x.get('created_at') or 0), reverse=True)
        return feed[:limit]
    except Exception as e:
        logger.error(f"Error building staff request feed: {e}")
        return []


def get_appointment(booking_id: str) -> Optional[Dict]:
    """Get appointment by booking ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM appointments WHERE booking_id = ?', (booking_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        return None


def get_latest_appointment(user_id: str) -> Optional[Dict]:
    """Get the most recent appointment for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean phone number for search
            phone_clean = user_id.lstrip('+').lstrip('91')
            
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE user_id = ? OR phone = ? 
                   OR user_id LIKE ? OR phone LIKE ?
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (user_id, user_id, f'%{phone_clean}%', f'%{phone_clean}%'))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting latest appointment: {e}")
        return None




def get_user_appointments(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all appointments for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            phone_clean = user_id.lstrip('+').lstrip('91')
            
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE user_id = ? OR phone = ? OR user_id LIKE ? OR phone LIKE ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, user_id, f'%{phone_clean}%', f'%{phone_clean}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting user appointments: {e}")
        return []


def cancel_appointment(
    booking_id: str,
    cancelled_by: str = 'patient',
    cancel_reason: str = None
) -> bool:
    """Cancel an appointment."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE appointments
                SET status = ?, updated_at = ?, cancelled_at = ?, cancelled_by = ?, cancel_reason = ?
                WHERE booking_id = ? AND status != 'cancelled'
                ''',
                ('cancelled', time.time(), time.time(), cancelled_by, cancel_reason, booking_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return False


def set_patient_hospital_id(patient_id: int, hospital_patient_id: str) -> bool:
    """Set or update hospital patient ID for an existing CRM patient."""
    if not hospital_patient_id or not str(hospital_patient_id).strip():
        return False

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE patients SET hospital_patient_id = ?, last_touch = ? WHERE id = ?',
                (str(hospital_patient_id).strip(), time.time(), patient_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating hospital patient ID: {e}")
        return False


def set_patient_automation_paused(patient_id: int, paused: bool) -> bool:
    """Enable/disable bot automation for a patient profile."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE patients SET automation_paused = ?, last_touch = ? WHERE id = ?',
                (1 if paused else 0, time.time(), patient_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating automation_paused: {e}")
        return False


def is_patient_automation_paused(external_id: str, platform: str = 'whatsapp') -> bool:
    """Check whether automation is paused for the given external user identity."""
    if not external_id:
        return False

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT automation_paused
                FROM patients
                WHERE external_id = ? AND platform = ?
                LIMIT 1
                ''',
                (external_id, platform)
            )
            row = cursor.fetchone()
            if row:
                return bool(row['automation_paused'])

            # WhatsApp identity can also exist in phone column.
            if platform == 'whatsapp':
                cursor.execute(
                    '''
                    SELECT automation_paused
                    FROM patients
                    WHERE phone = ? AND platform = 'whatsapp'
                    LIMIT 1
                    ''',
                    (external_id,)
                )
                row = cursor.fetchone()
                if row:
                    return bool(row['automation_paused'])

            return False
    except Exception as e:
        logger.error(f"Error checking automation_paused: {e}")
        return False


def get_all_appointments(
    status: str = None, 
    date_from: str = None, 
    date_to: str = None,
    limit: int = 100
) -> List[Dict]:
    """Get all appointments with optional filters - for CRM dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM appointments WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            if date_from:
                query += ' AND date >= ?'
                params.append(date_from)
            if date_to:
                query += ' AND date <= ?'
                params.append(date_to)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting all appointments: {e}")
        return []


# ============================================================================
# DIAGNOSTICS FUNCTIONS
# ============================================================================

def save_diagnostic(
    booking_id: str,
    user_id: str,
    patient_name: str,
    test_type: str,
    date: str = None,
    time_slot: str = None,
    phone: str = None,
    clinic_id: str = 'default',
    source: str = 'whatsapp'
) -> bool:
    """Save a diagnostic booking."""
    try:
        # Auto-detect source from user_id if it's the default 'whatsapp'
        if source == 'whatsapp':
            if user_id.startswith('instagram_'):
                source = 'instagram'
            elif user_id.startswith('facebook_'):
                source = 'facebook'

        # Use user_id as phone if not provided
        if not phone:
            phone = user_id
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnostics 
                (booking_id, user_id, patient_name, phone, test_type, date, time, clinic_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (booking_id, user_id, patient_name, phone, test_type, date, time_slot, clinic_id, source))
            conn.commit()
            
            # Update CRM patient diagnostics count
            _increment_patient_diagnostics(user_id)
            
            logger.info(f"Diagnostic booking saved: {booking_id} via {source}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Diagnostic {booking_id} already exists")
        return False
    except Exception as e:
        logger.error(f"Error saving diagnostic: {e}")
        return False


def get_diagnostic(booking_id: str) -> Optional[Dict]:
    """Get diagnostic booking by ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM diagnostics WHERE booking_id = ?', (booking_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting diagnostic: {e}")
        return None


def get_user_diagnostics(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all diagnostic bookings for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            phone_clean = user_id.lstrip('+').lstrip('91')
            
            cursor.execute('''
                SELECT * FROM diagnostics 
                WHERE user_id = ? OR phone = ? OR user_id LIKE ? OR phone LIKE ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, user_id, f'%{phone_clean}%', f'%{phone_clean}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting user diagnostics: {e}")
        return []


def get_all_diagnostics(
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100
) -> List[Dict]:
    """Get all diagnostic bookings - for CRM dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM diagnostics WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            if date_from:
                query += ' AND date >= ?'
                params.append(date_from)
            if date_to:
                query += ' AND date <= ?'
                params.append(date_to)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting all diagnostics: {e}")
        return []


# ============================================================================
# ADMISSION FUNCTIONS
# ============================================================================

def save_admission(
    admission_id: str,
    user_id: str,
    patient_name: str,
    age: str = None,
    sex: str = None,
    admission_type: str = 'non-emergency',
    preferred_date: str = None,
    phone: str = None,
    is_walkin: bool = False,
    clinic_id: str = 'default',
    source: str = 'whatsapp'
) -> bool:
    """Save an admission request."""
    try:
        # Auto-detect source from user_id if it's the default 'whatsapp'
        if source == 'whatsapp':
            if user_id.startswith('instagram_'):
                source = 'instagram'
            elif user_id.startswith('facebook_'):
                source = 'facebook'

        # Use user_id as phone if not provided
        if not phone:
            phone = user_id
            
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admissions 
                (admission_id, user_id, patient_name, phone, age, sex, 
                 admission_type, preferred_date, is_walkin, clinic_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (admission_id, user_id, patient_name, phone, age, sex,
                  admission_type, preferred_date, 1 if is_walkin else 0, clinic_id, source))
            conn.commit()
            
            # Update CRM patient admissions count
            _increment_patient_admissions(user_id)
            
            logger.info(f"Admission request saved: {admission_id} via {source}")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Admission {admission_id} already exists")
        return False
    except Exception as e:
        logger.error(f"Error saving admission: {e}")
        return False


def get_admission(admission_id: str) -> Optional[Dict]:
    """Get admission by ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admissions WHERE admission_id = ?', (admission_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting admission: {e}")
        return None


def get_user_admissions(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all admission requests for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            phone_clean = user_id.lstrip('+').lstrip('91')
            
            cursor.execute('''
                SELECT * FROM admissions 
                WHERE user_id = ? OR phone = ? OR user_id LIKE ? OR phone LIKE ?
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, user_id, f'%{phone_clean}%', f'%{phone_clean}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting user admissions: {e}")
        return []


def get_all_admissions(
    status: str = None,
    admission_type: str = None,
    limit: int = 100
) -> List[Dict]:
    """Get all admission requests - for CRM dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM admissions WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            if admission_type:
                query += ' AND admission_type = ?'
                params.append(admission_type)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting all admissions: {e}")
        return []


def update_admission_status(admission_id: str, status: str) -> bool:
    """Update admission status."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE admissions SET status = ?, updated_at = ? WHERE admission_id = ?',
                (status, time.time(), admission_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating admission status: {e}")
        return False


# ============================================================================
# SESSION FUNCTIONS
# ============================================================================

def get_session(user_id: str, timeout: int = 1800) -> Optional[Dict]:
    """Get active session for user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                # Check if expired
                if (time.time() - data['updated_at']) > timeout:
                    delete_session(user_id)
                    return None
                # Parse JSON data
                if data['data']:
                    data['data'] = json.loads(data['data'])
                else:
                    data['data'] = {}
                return data
            return None
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return None


def save_session(user_id: str, step: str, data: dict, session_type: str = 'appointment'):
    """Save or update session."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            data_json = json.dumps(data)
            now = time.time()
            
            cursor.execute('''
                INSERT INTO sessions (user_id, step, data, session_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    step = excluded.step,
                    data = excluded.data,
                    session_type = excluded.session_type,
                    updated_at = excluded.updated_at
            ''', (user_id, step, data_json, session_type, now, now))
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving session: {e}")


def delete_session(user_id: str):
    """Delete session for user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting session: {e}")


def session_exists(user_id: str, timeout: int = 1800) -> bool:
    """Check if active session exists."""
    session = get_session(user_id, timeout)
    return session is not None


# ============================================================================
# CRM / PATIENT FUNCTIONS
# ============================================================================

def get_patient(external_id: str, platform: str = 'whatsapp') -> Optional[Dict]:
    """Get patient by external ID and platform."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM patients WHERE external_id = ? AND platform = ?',
                (external_id, platform)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting patient: {e}")
        return None


def get_patient_by_phone(phone: str) -> Optional[Dict]:
    """Get patient by phone number (any format)."""
    try:
        phone_clean = phone.lstrip('+').lstrip('91')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM patients 
                WHERE phone = ? OR external_id = ? 
                   OR phone LIKE ? OR external_id LIKE ?
                LIMIT 1
            ''', (phone, phone, f'%{phone_clean}%', f'%{phone_clean}%'))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting patient by phone: {e}")
        return None


def onboard_patient(external_id: str, platform: str = 'whatsapp', name: str = None) -> int:
    """Create or update patient profile. Returns patient ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            
            # Try to get existing patient
            cursor.execute(
                'SELECT id FROM patients WHERE external_id = ? AND platform = ?',
                (external_id, platform)
            )
            row = cursor.fetchone()
            
            if row:
                # Update last touch and optionally name
                if name:
                    cursor.execute(
                        'UPDATE patients SET last_touch = ?, name = ? WHERE id = ?',
                        (now, name, row['id'])
                    )
                else:
                    cursor.execute(
                        'UPDATE patients SET last_touch = ? WHERE id = ?',
                        (now, row['id'])
                    )
                conn.commit()
                return row['id']
            else:
                # Create new patient
                phone = external_id if platform == 'whatsapp' else None
                cursor.execute('''
                    INSERT INTO patients (external_id, platform, name, phone, first_touch, last_touch)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (external_id, platform, name, phone, now, now))
                conn.commit()
                return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error onboarding patient: {e}")
        return 0


def update_patient_name(external_id: str, name: str, platform: str = 'whatsapp'):
    """Update patient name."""
    onboard_patient(external_id, platform, name)


def _increment_patient_appointments(user_id: str):
    """Internal: Increment appointment count for patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE patients SET total_appointments = total_appointments + 1, last_touch = ?
                WHERE external_id = ? OR phone = ?
            ''', (time.time(), user_id, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing appointments: {e}")


def _increment_patient_diagnostics(user_id: str):
    """Internal: Increment diagnostics count for patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE patients SET total_diagnostics = total_diagnostics + 1, last_touch = ?
                WHERE external_id = ? OR phone = ?
            ''', (time.time(), user_id, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing diagnostics: {e}")


def _increment_patient_admissions(user_id: str):
    """Internal: Increment admissions count for patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE patients SET total_admissions = total_admissions + 1, last_touch = ?
                WHERE external_id = ? OR phone = ?
            ''', (time.time(), user_id, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing admissions: {e}")


def increment_booking_count(patient_id: int):
    """Legacy: Increment total bookings count for patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE patients SET total_appointments = total_appointments + 1 WHERE id = ?',
                (patient_id,)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing booking count: {e}")


def log_interaction(
    patient_id: int,
    direction: str,
    platform: str,
    message: str,
    user_id: str = None,
    message_type: str = 'text',
    payload: str = None
):
    """Log an interaction to patient timeline."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO interactions 
                (patient_id, user_id, direction, platform, message_type, message, payload, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_id, user_id, direction, platform, message_type, 
                  message[:1000] if message else '', payload, time.time()))
            conn.commit()
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")


def get_patient_history(patient_id: int, limit: int = 50) -> List[Dict]:
    """Get interaction history for patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM interactions 
                WHERE patient_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (patient_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting patient history: {e}")
        return []


def get_chat_history(user_id: str, limit: int = 50) -> List[Dict]:
    """Get chat history by user_id (for CRM chatbox)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM interactions 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return []


def get_all_patients(limit: int = 100) -> List[Dict]:
    """Get all patients for CRM dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM patients 
                ORDER BY last_touch DESC LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting all patients: {e}")
        return []


# ============================================================================
# AI LOGGING
# ============================================================================

def log_ai_interaction(user_id: str, user_message: str, ai_response: str, model: str = 'gemini'):
    """Log AI interaction for analytics."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ai_interactions (user_id, user_message, ai_response, model, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, user_message[:1000], ai_response[:2000], model, time.time()))
            conn.commit()
    except Exception as e:
        logger.error(f"Error logging AI interaction: {e}")


# ============================================================================
# CONVERSATION STATE FUNCTIONS
# ============================================================================

def get_conversation_state(user_id: str) -> Optional[Dict]:
    """Get conversation state for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversation_state WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                # Parse context JSON if present
                if data.get('context'):
                    data['context'] = json.loads(data['context'])
                else:
                    data['context'] = {}
                return data
            return None
    except Exception as e:
        logger.error(f"Error getting conversation state: {e}")
        return None


def set_conversation_state(
    user_id: str,
    mode: str,
    sub_step: str = None,
    context: dict = None,
    flow_token: str = None
):
    """Set or update conversation state for a user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            context_json = json.dumps(context) if context else None
            now = time.time()
            
            cursor.execute('''
                INSERT INTO conversation_state (user_id, mode, sub_step, context, flow_token, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    mode = excluded.mode,
                    sub_step = excluded.sub_step,
                    context = excluded.context,
                    flow_token = excluded.flow_token,
                    updated_at = excluded.updated_at
            ''', (user_id, mode, sub_step, context_json, flow_token, now))
            conn.commit()
            logger.debug(f"Set conversation state for {user_id[:6]}***: mode={mode}")
    except Exception as e:
        logger.error(f"Error setting conversation state: {e}")


def update_conversation_context(user_id: str, context_updates: dict):
    """Update only the context field of conversation state (merge with existing)."""
    try:
        existing = get_conversation_state(user_id)
        if existing:
            current_context = existing.get('context', {}) or {}
            merged_context = {**current_context, **context_updates}
            
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversation_state 
                    SET context = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (json.dumps(merged_context), time.time(), user_id))
                conn.commit()
    except Exception as e:
        logger.error(f"Error updating conversation context: {e}")


def reset_conversation_state(user_id: str):
    """Reset user to MAIN_MENU state."""
    set_conversation_state(user_id, mode='MAIN_MENU', sub_step=None, context={}, flow_token=None)


def delete_conversation_state(user_id: str):
    """Delete conversation state for user."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversation_state WHERE user_id = ?', (user_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error deleting conversation state: {e}")


# ============================================================================
# DASHBOARD / STATS FUNCTIONS
# ============================================================================

def get_dashboard_stats() -> Dict[str, Any]:
    """Get overall stats for CRM dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Total counts
            cursor.execute('SELECT COUNT(*) FROM appointments')
            total_appointments = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM diagnostics')
            total_diagnostics = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM admissions')
            total_admissions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM patients')
            total_patients = cursor.fetchone()[0]
            
            # Today's bookings
            today = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute('SELECT COUNT(*) FROM appointments WHERE date = ?', (today,))
            today_appointments = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM diagnostics WHERE date = ?', (today,))
            today_diagnostics = cursor.fetchone()[0]
            
            # Pending admissions
            cursor.execute("SELECT COUNT(*) FROM admissions WHERE status = 'pending'")
            pending_admissions = cursor.fetchone()[0]
            
            return {
                'total_appointments': total_appointments,
                'total_diagnostics': total_diagnostics,
                'total_admissions': total_admissions,
                'total_patients': total_patients,
                'today_appointments': today_appointments,
                'today_diagnostics': today_diagnostics,
                'pending_admissions': pending_admissions
            }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}


def get_recent_bookings(limit: int = 20) -> List[Dict]:
    """Get recent bookings across all types for dashboard."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Union all booking types
            cursor.execute('''
                SELECT 'appointment' as type, booking_id as id, patient_name, phone, 
                       doctor as details, date, time, status, created_at
                FROM appointments
                UNION ALL
                SELECT 'diagnostic' as type, booking_id as id, patient_name, phone,
                       test_type as details, date, time, status, created_at
                FROM diagnostics
                UNION ALL
                SELECT 'admission' as type, admission_id as id, patient_name, phone,
                       admission_type as details, preferred_date as date, NULL as time, status, created_at
                FROM admissions
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting recent bookings: {e}")
        return []


# ============================================================================
# FLOW PERSISTENCE FUNCTIONS
# ============================================================================

def save_flow_data(flow_token: str, data: Dict[str, Any]):
    """Save or update Flow data persistently."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # Try to get existing data to merge
            cursor.execute('SELECT flow_data FROM flow_persistence WHERE flow_token = ?', (flow_token,))
            row = cursor.fetchone()
            
            if row:
                existing_data = json.loads(row['flow_data'])
                merged_data = {**existing_data, **data}
            else:
                merged_data = data
                
            cursor.execute('''
                INSERT OR REPLACE INTO flow_persistence (flow_token, flow_data, updated_at)
                VALUES (?, ?, ?)
            ''', (flow_token, json.dumps(merged_data), time.time()))
            conn.commit()
            logger.info(f"Persistent Flow data saved for token: {flow_token}")
    except Exception as e:
        logger.error(f"Error saving flow data: {e}")

def get_flow_data(flow_token: str) -> Dict[str, Any]:
    """Retrieve persistent Flow data."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT flow_data FROM flow_persistence WHERE flow_token = ?', (flow_token,))
            row = cursor.fetchone()
            if row:
                return json.loads(row['flow_data'])
    except Exception as e:
        logger.error(f"Error retrieving flow data: {e}")
    return {}

def clear_flow_data(flow_token: str):
    """Delete persistent Flow data."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM flow_persistence WHERE flow_token = ?', (flow_token,))
            conn.commit()
            logger.info(f"Persistent Flow data cleared for token: {flow_token}")
    except Exception as e:
        logger.error(f"Error clearing flow data: {e}")
# ============================================================================
# CRM AUTHENTICATION FUNCTIONS
# ============================================================================

def hash_password(password: str, salt: str = None) -> tuple:
    """Hash password with salt using SHA256."""
    import hashlib
    import secrets
    if not salt:
        salt = secrets.token_hex(16)
    
    encoded = (password + salt).encode('utf-8')
    pw_hash = hashlib.sha256(encoded).hexdigest()
    return pw_hash, salt

def create_crm_user(username: str, password: str, full_name: str = None, role: str = 'staff') -> bool:
    """Create a new CRM user."""
    try:
        pw_hash, salt = hash_password(password)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO crm_users (username, password_hash, salt, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, pw_hash, salt, full_name, role))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"Error creating CRM user: {e}")
        return False

def verify_crm_login(username: str, password: str) -> Optional[dict]:
    """Verify login credentials and return user info."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM crm_users WHERE username = ?', (username,))
            user_row = cursor.fetchone()
            
            if not user_row:
                return None
            
            user = dict(user_row)
            pw_hash, _ = hash_password(password, user['salt'])
            
            if pw_hash == user['password_hash']:
                # Update last login
                cursor.execute('UPDATE crm_users SET last_login = ? WHERE id = ?', (time.time(), user['id']))
                conn.commit()
                
                # Don't return sensitive data
                user.pop('password_hash')
                user.pop('salt')
                return user
            
            return None
    except Exception as e:
        logger.error(f"Error verifying CRM login: {e}")
        return None

def create_crm_session(user_id: int, expiry_days: int = 7) -> str:
    """Create a new session token."""
    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + (expiry_days * 86400)
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO crm_sessions (token, user_id, expires_at)
                VALUES (?, ?, ?)
            ''', (token, user_id, expires_at))
            conn.commit()
            return token
    except Exception as e:
        logger.error(f"Error creating CRM session: {e}")
        return None

def get_crm_session(token: str) -> Optional[dict]:
    """Retrieve and validate session."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, u.username, u.full_name, u.role 
                FROM crm_sessions s
                JOIN crm_users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > ?
            ''', (token, time.time()))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting CRM session: {e}")
        return None

def clear_crm_session(token: str):
    """Delete a session (logout)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM crm_sessions WHERE token = ?', (token,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error clearing CRM session: {e}")
