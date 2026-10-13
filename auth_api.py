"""
Authentication API for CRM Dashboard.
Handles login, logout, and session validation.
"""

import logging
from flask import Blueprint, request, jsonify
from database import verify_crm_login, create_crm_session, get_crm_session, clear_crm_session

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and create session."""
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
            
        user = verify_crm_login(username, password)
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
            
        token = create_crm_session(user['id'])
        if not token:
            return jsonify({'error': 'Failed to create session'}), 500
            
        return jsonify({
            'success': True,
            'token': token,
            'user': user
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Clear session token."""
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token.split(' ')[1]
        clear_crm_session(token)
    return jsonify({'success': True}), 200

@auth_bp.route('/api/auth/me', methods=['GET'])
def get_me():
    """Check if session is valid and return user info."""
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
        
    token = token.split(' ')[1]
    session = get_crm_session(token)
    
    if not session:
        return jsonify({'error': 'Session expired or invalid'}), 401
        
    return jsonify({
        'id': session['user_id'],
        'username': session['username'],
        'full_name': session['full_name'],
        'role': session['role']
    }), 200
