
import sqlite3
import os
import sys

# Add parent directory to path to import database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import save_appointment, get_latest_appointment

def test_channel_detection():
    print("Testing channel detection logic...")
    
    # 1. Test Instagram
    user_id_ig = "instagram_test_user_123"
    booking_id_ig = "APT_IG_TEST"
    
    save_appointment(
        booking_id=booking_id_ig,
        user_id=user_id_ig,
        patient_name="IG Test Patient",
        doctor="Dr. Mahesh Babu",
        date="2026-02-20",
        time_slot="10:30 AM",
        source="whatsapp" # This is the default that was causing the bug
    )
    
    appt_ig = get_latest_appointment(user_id_ig)
    if appt_ig and appt_ig['source'] == 'instagram':
        print("✅ Instagram source detected correctly!")
    else:
        print(f"❌ Instagram source detection failed. Got: {appt_ig['source'] if appt_ig else 'None'}")
        
    # 2. Test Facebook
    user_id_fb = "facebook_test_user_456"
    booking_id_fb = "APT_FB_TEST"
    
    save_appointment(
        booking_id=booking_id_fb,
        user_id=user_id_fb,
        patient_name="FB Test Patient",
        doctor="Dr. Mounika Reddy",
        date="2026-02-21",
        time_slot="11:30 AM",
        source="whatsapp"
    )
    
    appt_fb = get_latest_appointment(user_id_fb)
    if appt_fb and appt_fb['source'] == 'facebook':
        print("✅ Facebook source detected correctly!")
    else:
        print(f"❌ Facebook source detection failed. Got: {appt_fb['source'] if appt_fb else 'None'}")
        
    # 3. Test WhatsApp (Normal)
    user_id_wa = "919999999999"
    booking_id_wa = "APT_WA_TEST"
    
    save_appointment(
        booking_id=booking_id_wa,
        user_id=user_id_wa,
        patient_name="WA Test Patient",
        doctor="Dr. Rahul",
        date="2026-02-22",
        time_slot="02:30 PM",
        source="whatsapp"
    )
    
    appt_wa = get_latest_appointment(user_id_wa)
    if appt_wa and appt_wa['source'] == 'whatsapp':
        print("✅ WhatsApp source preserved correctly!")
    else:
        print(f"❌ WhatsApp source detection failed. Got: {appt_wa['source'] if appt_wa else 'None'}")

if __name__ == "__main__":
    test_channel_detection()
