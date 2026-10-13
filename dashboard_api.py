"""
Dashboard API - Production Ready
Complete REST endpoints for Hospital CRM Dashboard.
WhatsApp-focused - Instagram/Facebook to be connected later.
"""

import logging
import time
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, g
from database import (
    get_connection, get_patient, get_patient_history, 
    get_user_appointments, get_user_diagnostics, get_user_admissions,
    cancel_appointment as db_cancel_appointment,
    get_all_appointments, get_all_diagnostics, get_all_admissions,
    get_dashboard_stats, get_recent_bookings, get_all_patients,
    set_patient_hospital_id, set_patient_automation_paused,
    update_admission_status, log_interaction, get_crm_session,
    get_all_enquiries, update_enquiry_status,
    get_all_prescriptions, update_prescription_status,
    get_staff_notifications, mark_staff_notification_read,
    mark_all_staff_notifications_read, get_staff_request_feed,
)

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


def _is_placeholder_name(name: str) -> bool:
    v = (name or '').strip().lower()
    return (not v) or v in {'anonymous', 'unknown', 'unknown patient', 'patient'}


def _hydrate_patient_identity(cursor, patient: dict) -> dict:
    """
    Fill missing/placeholder patient name/phone from latest bookings.
    Keeps CRM UI useful even when profile onboarding didn't capture name yet.
    """
    external_id = patient.get('external_id') or ''
    current_phone = patient.get('phone') or ''

    if not external_id and not current_phone:
        return patient

    instagram_user_id = f"instagram_{external_id}" if external_id else ''
    facebook_user_id = f"facebook_{external_id}" if external_id else ''

    identity_params = (
        external_id, instagram_user_id, facebook_user_id, external_id, current_phone,
        external_id, instagram_user_id, facebook_user_id, external_id, current_phone,
        external_id, instagram_user_id, facebook_user_id, external_id, current_phone
    )

    cursor.execute(
        '''
        SELECT patient_name, phone, created_at FROM appointments
        WHERE (user_id = ? OR user_id = ? OR user_id = ? OR phone = ? OR phone = ?)
          AND patient_name IS NOT NULL AND TRIM(patient_name) <> ''
        UNION ALL
        SELECT patient_name, phone, created_at FROM diagnostics
        WHERE (user_id = ? OR user_id = ? OR user_id = ? OR phone = ? OR phone = ?)
          AND patient_name IS NOT NULL AND TRIM(patient_name) <> ''
        UNION ALL
        SELECT patient_name, phone, created_at FROM admissions
        WHERE (user_id = ? OR user_id = ? OR user_id = ? OR phone = ? OR phone = ?)
          AND patient_name IS NOT NULL AND TRIM(patient_name) <> ''
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        identity_params
    )
    latest = cursor.fetchone()
    if not latest:
        return patient

    latest_name = (latest['patient_name'] or '').strip()
    latest_phone = (latest['phone'] or '').strip()

    if _is_placeholder_name(patient.get('name')) and latest_name and not _is_placeholder_name(latest_name):
        patient['name'] = latest_name

    if (not (patient.get('phone') or '').strip()) and latest_phone:
        patient['phone'] = latest_phone

    return patient

# ============ AUTH DECORATOR ============

def require_auth(f):
    """Decorator to protect dashboard routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        session = get_crm_session(token)
        
        if not session:
            return jsonify({'error': 'Unauthorized', 'message': 'Session expired or invalid'}), 401
            
        # Store user info in flask global
        g.user = session
        return f(*args, **kwargs)
    return decorated

# ============ STATS & ANALYTICS ============

@dashboard_bp.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get high-level CRM statistics - WhatsApp focused."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Total Patients
            cursor.execute('SELECT COUNT(*) FROM patients')
            total_patients = cursor.fetchone()[0]
            
            # Total Confirmed Appointments
            cursor.execute('SELECT COUNT(*) FROM appointments WHERE status = "confirmed"')
            total_appointments = cursor.fetchone()[0]
            
            # Total Diagnostic Bookings
            cursor.execute('SELECT COUNT(*) FROM diagnostics WHERE status = "confirmed"')
            total_diagnostics = cursor.fetchone()[0]
            
            # Total Admission Requests
            cursor.execute('SELECT COUNT(*) FROM admissions')
            total_admissions = cursor.fetchone()[0]
            
            # Pending Admissions
            cursor.execute('SELECT COUNT(*) FROM admissions WHERE status = "pending"')
            pending_admissions = cursor.fetchone()[0]
            
            # Today's stats
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('SELECT COUNT(*) FROM appointments WHERE date = ? AND status = "confirmed"', (today,))
            today_appointments = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM diagnostics WHERE date = ? AND status = "confirmed"', (today,))
            today_diagnostics = cursor.fetchone()[0]
            
            # Recent Interactions (last 24h)
            day_ago = time.time() - 86400
            cursor.execute('SELECT COUNT(*) FROM interactions WHERE timestamp > ?', (day_ago,))
            recent_activity = cursor.fetchone()[0]
            
            # New Patients This Week
            week_ago = time.time() - (7 * 86400)
            cursor.execute('SELECT COUNT(*) FROM patients WHERE first_touch > ?', (week_ago,))
            new_patients_week = cursor.fetchone()[0]
            
            # Platform breakdown (WhatsApp for now)
            cursor.execute('SELECT platform, COUNT(*) as count FROM patients GROUP BY platform')
            platforms = {row['platform'] or 'whatsapp': row['count'] for row in cursor.fetchall()}
            
            # Department breakdown from appointments
            cursor.execute('''
                SELECT department_name, COUNT(*) as count 
                FROM appointments 
                WHERE status = "confirmed" AND department_name IS NOT NULL
                GROUP BY department_name
            ''')
            departments = {row['department_name']: row['count'] for row in cursor.fetchall()}
            
            # Test type breakdown from diagnostics
            cursor.execute('''
                SELECT test_type, COUNT(*) as count 
                FROM diagnostics 
                WHERE status = "confirmed"
                GROUP BY test_type
            ''')
            test_types = {row['test_type']: row['count'] for row in cursor.fetchall()}

            # Sudha-specific request counts
            try:
                cursor.execute('SELECT COUNT(*) FROM enquiries')
                total_enquiries = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM enquiries WHERE status = 'open'")
                open_enquiries = cursor.fetchone()[0]
            except Exception:
                total_enquiries = 0
                open_enquiries = 0
            try:
                cursor.execute('SELECT COUNT(*) FROM pharmacy_prescriptions')
                total_pharmacy = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM pharmacy_prescriptions WHERE status = 'pending'")
                pending_pharmacy = cursor.fetchone()[0]
            except Exception:
                total_pharmacy = 0
                pending_pharmacy = 0
            try:
                cursor.execute('SELECT COUNT(*) FROM staff_notifications WHERE is_read = 0')
                unread_notifications = cursor.fetchone()[0]
            except Exception:
                unread_notifications = 0

            return jsonify({
                'total_patients': total_patients,
                'total_appointments': total_appointments,
                'total_diagnostics': total_diagnostics,
                'total_admissions': total_admissions,
                'pending_admissions': pending_admissions,
                'today_appointments': today_appointments,
                'today_diagnostics': today_diagnostics,
                'recent_activity': recent_activity,
                'new_patients_week': new_patients_week,
                'platforms': platforms,
                'departments': departments,
                'test_types': test_types,
                'total_enquiries': total_enquiries,
                'open_enquiries': open_enquiries,
                'total_pharmacy': total_pharmacy,
                'pending_pharmacy': pending_pharmacy,
                'unread_notifications': unread_notifications,
            }), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (stats): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/analytics/weekly', methods=['GET'])
@require_auth
def get_weekly_analytics():
    """Get weekly trends for charts."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get last 7 days data
            days_data = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                day_name = (datetime.now() - timedelta(days=i)).strftime('%a')
                
                # Appointments on this day
                cursor.execute(
                    'SELECT COUNT(*) FROM appointments WHERE date = ? AND status = "confirmed"',
                    (date,)
                )
                appointments = cursor.fetchone()[0]
                
                # New patients on this day
                day_start = time.time() - (i * 86400) - (datetime.now().hour * 3600) - (datetime.now().minute * 60)
                day_end = day_start + 86400
                cursor.execute(
                    'SELECT COUNT(*) FROM patients WHERE first_touch >= ? AND first_touch < ?',
                    (day_start, day_end)
                )
                new_patients = cursor.fetchone()[0]
                
                # Interactions
                cursor.execute(
                    'SELECT COUNT(*) FROM interactions WHERE timestamp >= ? AND timestamp < ?',
                    (day_start, day_end)
                )
                interactions = cursor.fetchone()[0]
                
                days_data.append({
                    'day': day_name,
                    'date': date,
                    'appointments': appointments,
                    'new_patients': new_patients,
                    'interactions': interactions
                })
            
            return jsonify(days_data), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (weekly): {e}")
        return jsonify({'error': str(e)}), 500


# ============ PATIENTS ============

@dashboard_bp.route('/api/patients', methods=['GET'])
@require_auth
def list_patients():
    """List all patients with optional search and filters."""
    search = request.args.get('search', '')
    platform = request.args.get('platform', '')
    limit = request.args.get('limit', 50, type=int)
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM patients WHERE 1=1'
            params = []
            
            if search:
                query += ' AND (name LIKE ? OR phone LIKE ? OR external_id LIKE ? OR hospital_patient_id LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
            
            if platform and platform != 'all':
                query += ' AND platform = ?'
                params.append(platform)
            
            query += ' ORDER BY last_touch DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            patients = [_hydrate_patient_identity(cursor, dict(row)) for row in cursor.fetchall()]
            
            return jsonify(patients), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (patients): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/patients/<int:patient_id>', methods=['GET'])
@require_auth
def get_patient_detail(patient_id):
    """Get detailed patient profile with all booking history."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'Patient not found'}), 404
            
            patient = dict(row)
            patient = _hydrate_patient_identity(cursor, patient)
            external_id = patient['external_id']
            
            # Get appointments
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE user_id = ? OR phone = ?
                ORDER BY created_at DESC
            ''', (external_id, external_id))
            patient['appointments'] = [dict(r) for r in cursor.fetchall()]
            
            # Get diagnostics
            cursor.execute('''
                SELECT * FROM diagnostics 
                WHERE user_id = ? OR phone = ?
                ORDER BY created_at DESC
            ''', (external_id, external_id))
            patient['diagnostics'] = [dict(r) for r in cursor.fetchall()]
            
            # Get admissions
            cursor.execute('''
                SELECT * FROM admissions 
                WHERE user_id = ? OR phone = ?
                ORDER BY created_at DESC
            ''', (external_id, external_id))
            patient['admissions'] = [dict(r) for r in cursor.fetchall()]
            
            # Get recent interactions
            cursor.execute('''
                SELECT * FROM interactions 
                WHERE patient_id = ? OR user_id = ?
                ORDER BY timestamp DESC LIMIT 50
            ''', (patient_id, external_id))
            patient['interactions'] = [dict(r) for r in cursor.fetchall()]
            
            return jsonify(patient), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (patient detail): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/patients/<int:patient_id>/timeline', methods=['GET'])
@require_auth
def get_timeline(patient_id):
    """Get full interaction timeline for a patient."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM interactions 
                WHERE patient_id = ? 
                ORDER BY timestamp DESC
            ''', (patient_id,))
            interactions = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            row = cursor.fetchone()
            patient = _hydrate_patient_identity(cursor, dict(row)) if row else {}
            
            return jsonify({
                'patient': patient,
                'interactions': interactions
            }), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (timeline): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/patients/<int:patient_id>/notes', methods=['PUT'])
@require_auth
def update_patient_notes(patient_id):
    """Update patient notes."""
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE patients SET notes = ? WHERE id = ?', (notes, patient_id))
            conn.commit()
            
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (update notes): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/patients/<int:patient_id>/hospital-id', methods=['PUT'])
@require_auth
def update_patient_hospital_id(patient_id):
    """Update hospital/system patient ID for CRM profile."""
    try:
        data = request.get_json() or {}
        hospital_patient_id = (data.get('hospital_patient_id') or '').strip()
        if not hospital_patient_id:
            return jsonify({'error': 'hospital_patient_id is required'}), 400

        success = set_patient_hospital_id(patient_id, hospital_patient_id)
        if not success:
            return jsonify({'error': 'Patient not found'}), 404

        return jsonify({'success': True, 'hospital_patient_id': hospital_patient_id}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (update hospital id): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/patients/<int:patient_id>/automation', methods=['PUT'])
@require_auth
def update_patient_automation(patient_id):
    """Toggle bot automation for a patient."""
    try:
        data = request.get_json() or {}
        paused = bool(data.get('paused', False))
        success = set_patient_automation_paused(patient_id, paused)
        if not success:
            return jsonify({'error': 'Patient not found'}), 404
        return jsonify({'success': True, 'paused': paused}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (update automation): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/send-message', methods=['POST'])
@require_auth
def send_message_from_crm():
    """Send a WhatsApp message from CRM (receptionist) to a patient."""
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        message = (data.get('message') or '').strip()
        if not patient_id or not message:
            return jsonify({'error': 'patient_id and message required'}), 400
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
            row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Patient not found'}), 404
        patient = dict(row)
        platform = (patient.get('platform') or 'whatsapp').lower()
        user_id = patient.get('external_id') or patient.get('phone') or ''
        if not user_id:
            return jsonify({'error': 'Patient has no contact (external_id/phone)'}), 400
        if platform == 'whatsapp':
            from whatsapp_client import send_text_message
            success = send_text_message(user_id, message)
        else:
            from app import send_message
            success = send_message(platform, user_id, message)
        if not success:
            return jsonify({'error': 'Failed to send message'}), 500
        log_interaction(patient_id, 'outbound', platform, message[:1000], user_id=user_id)
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (send-message): {e}")
        return jsonify({'error': str(e)}), 500


# ============ APPOINTMENTS ============

@dashboard_bp.route('/api/appointments', methods=['GET'])
@require_auth
def list_appointments():
    """List appointments with filters (status, date, department, source/channel)."""
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    department = request.args.get('department', '')
    source = request.args.get('source', '')  # whatsapp, instagram, facebook
    search = request.args.get('search', '')
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM appointments WHERE 1=1'
            params = []
            
            if status and status != 'all':
                query += ' AND status = ?'
                params.append(status)
            
            if date_from:
                query += ' AND date >= ?'
                params.append(date_from)
            
            if date_to:
                query += ' AND date <= ?'
                params.append(date_to)
            
            if department and department != 'all':
                query += ' AND department = ?'
                params.append(department)
            
            if source and source != 'all':
                query += ' AND COALESCE(source, "whatsapp") = ?'
                params.append(source)
            
            if search:
                query += ' AND (patient_name LIKE ? OR booking_id LIKE ? OR phone LIKE ? OR patient_identifier LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
            
            query += ' ORDER BY date DESC, time ASC'
            
            cursor.execute(query, params)
            appointments = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(appointments), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (appointments): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/appointments/today', methods=['GET'])
@require_auth
def get_today_appointments():
    """Get today's appointment schedule."""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE date = ? AND status = "confirmed"
                ORDER BY time ASC
            ''', (today,))
            appointments = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(appointments), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (today): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/appointments/upcoming', methods=['GET'])
@require_auth
def get_upcoming_appointments():
    """Get upcoming appointments for next 7 days."""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE date >= ? AND date <= ? AND status = "confirmed"
                ORDER BY date ASC, time ASC
            ''', (today, next_week))
            appointments = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(appointments), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (upcoming): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/appointments/<booking_id>/cancel', methods=['POST'])
@require_auth
def cancel_appointment(booking_id):
    """Cancel an appointment."""
    try:
        data = request.get_json(silent=True) or {}
        cancel_reason = (data.get('reason') or '').strip() or None
        cancelled_by = (data.get('cancelled_by') or 'staff').strip() or 'staff'

        success = db_cancel_appointment(
            booking_id,
            cancelled_by=cancelled_by,
            cancel_reason=cancel_reason
        )
        if success:
            return jsonify({'success': True, 'message': 'Appointment cancelled'}), 200
        else:
            return jsonify({'error': 'Appointment not found'}), 404
    except Exception as e:
        logger.error(f"Dashboard API Error (cancel): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/appointments/<booking_id>/status', methods=['PUT'])
@require_auth
def update_appointment_status(booking_id):
    """Update appointment status (confirmed, completed, no-show, cancelled)."""
    try:
        data = request.get_json() or {}
        status = (data.get('status') or 'confirmed').strip().lower()
        valid_statuses = {'confirmed', 'completed', 'no-show', 'cancelled'}
        if status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        with get_connection() as conn:
            cursor = conn.cursor()
            if status == 'cancelled':
                cancel_reason = (data.get('reason') or '').strip() or None
                cancelled_by = (data.get('cancelled_by') or 'staff').strip() or 'staff'
                cursor.execute(
                    '''
                    UPDATE appointments
                    SET status = ?, updated_at = ?, cancelled_at = ?, cancelled_by = ?, cancel_reason = ?
                    WHERE booking_id = ?
                    ''',
                    (status, time.time(), time.time(), cancelled_by, cancel_reason, booking_id)
                )
            else:
                cursor.execute(
                    '''
                    UPDATE appointments
                    SET status = ?, updated_at = ?
                    WHERE booking_id = ?
                    ''',
                    (status, time.time(), booking_id)
                )
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({'success': True}), 200
            else:
                return jsonify({'error': 'Appointment not found'}), 404
    except Exception as e:
        logger.error(f"Dashboard API Error (update status): {e}")
        return jsonify({'error': str(e)}), 500


# ============ LIVE FEED ============

@dashboard_bp.route('/api/live-feed', methods=['GET'])
@require_auth
def live_feed():
    """Get most recent interactions across all platforms."""
    limit = request.args.get('limit', 20, type=int)
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, p.name as patient_name, p.external_id, p.platform
                FROM interactions i
                LEFT JOIN patients p ON i.patient_id = p.id
                ORDER BY i.timestamp DESC LIMIT ?
            ''', (limit,))
            feed = [dict(row) for row in cursor.fetchall()]
            return jsonify(feed), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (live-feed): {e}")
        return jsonify({'error': str(e)}), 500


# ============ DEPARTMENTS ============

@dashboard_bp.route('/api/departments', methods=['GET'])
@require_auth
def get_departments():
    """Get list of departments with stats."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    department_name,
                    department,
                    COUNT(*) as total_appointments,
                    SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                FROM appointments 
                GROUP BY department
            ''')
            departments = [dict(row) for row in cursor.fetchall()]
            return jsonify(departments), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (departments): {e}")
        return jsonify({'error': str(e)}), 500


# ============ DIAGNOSTICS ============

@dashboard_bp.route('/api/diagnostics', methods=['GET'])
@require_auth
def list_diagnostics():
    """List diagnostic bookings with filters."""
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    search = request.args.get('search', '')
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM diagnostics WHERE 1=1'
            params = []
            
            if status and status != 'all':
                query += ' AND status = ?'
                params.append(status)
            
            if date_from:
                query += ' AND date >= ?'
                params.append(date_from)
            
            if date_to:
                query += ' AND date <= ?'
                params.append(date_to)
            
            if search:
                query += ' AND (patient_name LIKE ? OR booking_id LIKE ? OR test_type LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            diagnostics = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(diagnostics), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (diagnostics): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/diagnostics/today', methods=['GET'])
@require_auth
def get_today_diagnostics():
    """Get today's diagnostic appointments."""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM diagnostics 
                WHERE date = ? AND status = "confirmed"
                ORDER BY time ASC
            ''', (today,))
            diagnostics = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(diagnostics), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (diagnostics today): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/diagnostics/<booking_id>/status', methods=['PUT'])
@require_auth
def update_diagnostic_status(booking_id):
    """Update diagnostic booking status."""
    try:
        data = request.get_json()
        status = data.get('status', 'confirmed')
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE diagnostics SET status = ?, updated_at = ? WHERE booking_id = ?',
                (status, time.time(), booking_id)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                return jsonify({'success': True}), 200
            else:
                return jsonify({'error': 'Diagnostic booking not found'}), 404
    except Exception as e:
        logger.error(f"Dashboard API Error (update diagnostic status): {e}")
        return jsonify({'error': str(e)}), 500


# ============ ADMISSIONS ============

@dashboard_bp.route('/api/admissions', methods=['GET'])
@require_auth
def list_admissions():
    """List admission requests with filters."""
    status = request.args.get('status', '')
    admission_type = request.args.get('type', '')
    search = request.args.get('search', '')
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM admissions WHERE 1=1'
            params = []
            
            if status and status != 'all':
                query += ' AND status = ?'
                params.append(status)
            
            if admission_type and admission_type != 'all':
                query += ' AND admission_type = ?'
                params.append(admission_type)
            
            if search:
                query += ' AND (patient_name LIKE ? OR admission_id LIKE ? OR phone LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
            
            query += ' ORDER BY created_at DESC'
            
            cursor.execute(query, params)
            admissions = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(admissions), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (admissions): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/admissions/pending', methods=['GET'])
@require_auth
def get_pending_admissions():
    """Get pending admission requests."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM admissions 
                WHERE status = "pending"
                ORDER BY created_at DESC
            ''')
            admissions = [dict(row) for row in cursor.fetchall()]
            
            return jsonify(admissions), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (pending admissions): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/admissions/<admission_id>/status', methods=['PUT'])
@require_auth
def update_admission_status_api(admission_id):
    """Update admission request status (pending, confirmed, admitted, discharged, cancelled)."""
    try:
        data = request.get_json()
        status = data.get('status', 'pending')
        
        success = update_admission_status(admission_id, status)
        
        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Admission not found'}), 404
    except Exception as e:
        logger.error(f"Dashboard API Error (update admission status): {e}")
        return jsonify({'error': str(e)}), 500


# ============ COMBINED DASHBOARD ============

@dashboard_bp.route('/api/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    """Get comprehensive dashboard data - all stats in one call."""
    try:
        stats = get_dashboard_stats()
        recent = get_recent_bookings(limit=20)
        
        return jsonify({
            'stats': stats,
            'recent_bookings': recent
        }), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (dashboard): {e}")
        return jsonify({'error': str(e)}), 500


# ============ SUDHA STAFF REQUESTS ============

@dashboard_bp.route('/api/staff/requests', methods=['GET'])
@require_auth
def staff_requests_feed():
    """Unified Sudha front-desk inbox (OPD / Ultrasound / Lab / Pharmacy / IPD)."""
    limit = request.args.get('limit', 200, type=int)
    kind = (request.args.get('kind') or '').strip().lower()
    flow = (request.args.get('flow') or '').strip().lower()
    queue = (request.args.get('queue') or '').strip().lower()  # action | today | all
    try:
        feed = get_staff_request_feed(limit=max(limit, 300))
        if kind and kind != 'all':
            feed = [item for item in feed if item.get('kind') == kind]
        if flow and flow != 'all':
            feed = [item for item in feed if item.get('flow') == flow]

        if queue == 'action':
            feed = [item for item in feed if item.get('needs_action')]
        elif queue == 'today':
            today = datetime.now().strftime('%Y-%m-%d')
            feed = [
                item for item in feed
                if (item.get('date') == today)
                or (
                    item.get('needs_action')
                    and item.get('flow') in ('pharmacy', 'ipd', 'alert')
                )
            ]

        return jsonify(feed[:limit]), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (staff requests): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/enquiries', methods=['GET'])
@require_auth
def list_enquiries():
    status = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    try:
        return jsonify(get_all_enquiries(status=status, limit=limit)), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (enquiries): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/enquiries/<enquiry_id>/status', methods=['PUT'])
@require_auth
def set_enquiry_status(enquiry_id):
    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if not status:
        return jsonify({'error': 'status required'}), 400
    try:
        ok = update_enquiry_status(enquiry_id, status)
        if not ok:
            return jsonify({'error': 'Enquiry not found'}), 404
        return jsonify({'success': True, 'enquiry_id': enquiry_id, 'status': status}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (enquiry status): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/pharmacy', methods=['GET'])
@require_auth
def list_pharmacy():
    status = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    try:
        return jsonify(get_all_prescriptions(status=status, limit=limit)), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (pharmacy): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/pharmacy/<request_id>/status', methods=['PUT'])
@require_auth
def set_pharmacy_status(request_id):
    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if not status:
        return jsonify({'error': 'status required'}), 400
    try:
        ok = update_prescription_status(request_id, status)
        if not ok:
            return jsonify({'error': 'Pharmacy request not found'}), 404
        return jsonify({'success': True, 'request_id': request_id, 'status': status}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (pharmacy status): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/staff/notifications', methods=['GET'])
@require_auth
def list_staff_notifications():
    unread_only = request.args.get('unread', '0') in ('1', 'true', 'True')
    limit = request.args.get('limit', 100, type=int)
    try:
        return jsonify(get_staff_notifications(unread_only=unread_only, limit=limit)), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (staff notifications): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/staff/notifications/<int:notification_id>/read', methods=['POST'])
@require_auth
def read_staff_notification(notification_id):
    try:
        ok = mark_staff_notification_read(notification_id)
        if not ok:
            return jsonify({'error': 'Notification not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (read notification): {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/staff/notifications/read-all', methods=['POST'])
@require_auth
def read_all_staff_notifications():
    try:
        mark_all_staff_notifications_read()
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (read all notifications): {e}")
        return jsonify({'error': str(e)}), 500


# ============ CHAT HISTORY ============

@dashboard_bp.route('/api/chat/<user_id>', methods=['GET'])
@require_auth
def get_chat_history(user_id):
    """Get chat history for a specific user (for CRM chatbox)."""
    limit = request.args.get('limit', 50, type=int)
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute('''
                SELECT * FROM patients 
                WHERE external_id = ? OR phone = ?
                LIMIT 1
            ''', (user_id, user_id))
            patient_row = cursor.fetchone()
            patient = dict(patient_row) if patient_row else None
            
            # Get interactions
            cursor.execute('''
                SELECT * FROM interactions 
                WHERE user_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (user_id, limit))
            messages = [dict(row) for row in cursor.fetchall()]
            
            # Get bookings
            appointments = get_user_appointments(user_id, limit=5)
            diagnostics = get_user_diagnostics(user_id, limit=5)
            admissions = get_user_admissions(user_id, limit=5)
            
            return jsonify({
                'patient': patient,
                'messages': messages,
                'appointments': appointments,
                'diagnostics': diagnostics,
                'admissions': admissions
            }), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (chat history): {e}")
        return jsonify({'error': str(e)}), 500


# ============ SEARCH ============

@dashboard_bp.route('/api/search', methods=['GET'])
@require_auth
def global_search():
    """Global search across patients, appointments, diagnostics, and admissions."""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify({
            'patients': [], 
            'appointments': [],
            'diagnostics': [],
            'admissions': []
        }), 200
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Search patients
            cursor.execute('''
                SELECT * FROM patients 
                WHERE name LIKE ? OR phone LIKE ? OR external_id LIKE ? OR hospital_patient_id LIKE ?
                LIMIT 10
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            patients = [dict(row) for row in cursor.fetchall()]
            
            # Search appointments
            cursor.execute('''
                SELECT * FROM appointments 
                WHERE patient_name LIKE ? OR booking_id LIKE ? OR phone LIKE ? OR patient_identifier LIKE ?
                LIMIT 10
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            appointments = [dict(row) for row in cursor.fetchall()]
            
            # Search diagnostics
            cursor.execute('''
                SELECT * FROM diagnostics 
                WHERE patient_name LIKE ? OR booking_id LIKE ? OR phone LIKE ? OR test_type LIKE ?
                LIMIT 10
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            diagnostics = [dict(row) for row in cursor.fetchall()]
            
            # Search admissions
            cursor.execute('''
                SELECT * FROM admissions 
                WHERE patient_name LIKE ? OR admission_id LIKE ? OR phone LIKE ?
                LIMIT 10
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
            admissions = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'patients': patients,
                'appointments': appointments,
                'diagnostics': diagnostics,
                'admissions': admissions
            }), 200
    except Exception as e:
        logger.error(f"Dashboard API Error (search): {e}")
        return jsonify({'error': str(e)}), 500
