import sqlite3
import time
import random

DATABASE_FILE = 'clinic_bot.db'

def simulate_booking():
    booking_id = f"TEST-{random.randint(1000, 9999)}"
    user_id = "test_user_123"
    patient_name = "Realtime Test Patient"
    doctor = "Dr. Notification"
    apt_date = "20-02-2026"
    apt_time = "10:30 AM"
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Insert a dummy appointment
    cursor.execute('''
        INSERT INTO appointments 
        (booking_id, user_id, patient_name, phone, department, department_name, 
         doctor, date, time, clinic_id, service_type, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (booking_id, user_id, patient_name, "9876543210", "General", "General Medicine",
          doctor, apt_date, apt_time, "default", "appointment", "whatsapp"))
    
    conn.commit()
    conn.close()
    
    print(f"Success! Inserted test booking: {booking_id}")
    print("Check your CRM dashboard. A notification should appear within 15 seconds.")

if __name__ == "__main__":
    simulate_booking()
