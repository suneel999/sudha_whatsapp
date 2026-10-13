"""
Verification script for Advanced CRM
"""
import sys
import os
import sqlite3

# Add current directory to path
sys.path.append(os.getcwd())

from database import init_database, get_connection
from crm_handler import process_crm_message, get_crm_context, handle_booking_confirmed, update_patient_name

def test_crm_onboarding():
    print("--- Testing Patient Onboarding & History ---")
    
    # Reset or ensures DB is fresh for Mallika Hospitals if needed, 
    # but here we just test logic.
    external_id = "919999988888"
    platform = "whatsapp"
    
    # 1. First interaction
    pid1 = process_crm_message(external_id, platform, "Hi, I want to book an appointment")
    print(f"User onboarded. Patient ID: {pid1}")
    
    # 2. Second interaction
    pid2 = process_crm_message(external_id, platform, "Is Dr. Mahesh available?")
    print(f"Returning user logged. Same ID? {'YES' if pid1 == pid2 else 'NO'}")
    
    # 3. Check context
    context = get_crm_context(external_id, platform)
    print("\nAI CRM Context (New User):")
    print(context)
    
    # 4. Simulate booking
    update_patient_name(external_id, platform, "Suneel Kumar")
    handle_booking_confirmed(external_id, platform)
    
    # 5. Check context again (Returning User)
    context_v2 = get_crm_context(external_id, platform)
    print("\nAI CRM Context (Returning VIP/Loyal):")
    print(context_v2)

def test_interaction_timeline():
    print("\n--- Testing Interaction Timeline ---")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interactions ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        print(f"Logged {len(rows)} interactions:")
        for row in rows:
            print(f"[{row['direction']}] {row['platform']}: {row['content'][:50]}...")

if __name__ == "__main__":
    init_database()
    test_crm_onboarding()
    test_interaction_timeline()
    print("\nCRM Verification complete!")
