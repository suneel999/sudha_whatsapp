"""
Clear Bookings Script
Clears all bookings (appointments, diagnostics, admissions) but keeps patient data.

Run: python clear_bookings.py
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_FILE = 'clinic_bot.db'


def clear_bookings():
    """Clear all booking data while preserving patient records."""
    
    print("=" * 60)
    print("CLEAR BOOKINGS TOOL")
    print("=" * 60)
    print()
    print("This will DELETE:")
    print("  - All appointments")
    print("  - All diagnostic bookings")
    print("  - All admission requests")
    print()
    print("This will KEEP:")
    print("  - Patient records")
    print("  - Chat history/interactions")
    print()
    
    confirm = input("Type 'CLEAR' to confirm: ").strip()
    
    if confirm != 'CLEAR':
        print("Cancelled. No changes made.")
        return
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Clear appointments
        cursor.execute('DELETE FROM appointments')
        apt_count = cursor.rowcount
        
        # Clear diagnostics
        cursor.execute('DELETE FROM diagnostics')
        diag_count = cursor.rowcount
        
        # Clear admissions
        cursor.execute('DELETE FROM admissions')
        adm_count = cursor.rowcount
        
        # Reset patient booking counts
        cursor.execute('''
            UPDATE patients SET 
                total_bookings = 0,
                total_appointments = 0,
                total_diagnostics = 0,
                total_admissions = 0
        ''')
        
        # Clear conversation states
        cursor.execute('DELETE FROM conversation_state')
        
        # Clear sessions
        cursor.execute('DELETE FROM sessions')
        
        conn.commit()
        conn.close()
        
        print()
        print(f"Deleted {apt_count} appointments")
        print(f"Deleted {diag_count} diagnostic bookings")
        print(f"Deleted {adm_count} admission requests")
        print("Reset patient booking counts")
        print("Cleared conversation states and sessions")
        print()
        print("=" * 60)
        print("Bookings cleared successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    clear_bookings()
