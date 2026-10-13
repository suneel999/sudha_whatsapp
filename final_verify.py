
import sqlite3
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import save_appointment

def final_test():
    db_path = 'clinic_bot.db'
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM appointments WHERE booking_id LIKE 'FINAL_TEST_%'")
    conn.commit()
    
    # Test cases
    test_cases = [
        ("FINAL_TEST_IG", "instagram_user_1", "IG Patient"),
        ("FINAL_TEST_FB", "facebook_user_1", "FB Patient"),
        ("FINAL_TEST_WA", "9100000000", "WA Patient")
    ]
    
    for bid, uid, name in test_cases:
        save_appointment(bid, uid, name, source="whatsapp") # default
        
    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT booking_id, user_id, source FROM appointments WHERE booking_id LIKE 'FINAL_TEST_%'")
    rows = cursor.fetchall()
    
    print("--- Final Database Channel Verification ---")
    for row in rows:
        print(f"Booking: {row[0]} | User: {row[1]} | Detected Source: {row[2]}")
        
    conn.close()

if __name__ == "__main__":
    final_test()
