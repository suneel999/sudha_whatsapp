"""View database contents - appointments and sessions"""
import sqlite3
from datetime import datetime

def view_appointments():
    conn = sqlite3.connect('clinic_bot.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 70)
    print("APPOINTMENTS")
    print("=" * 70)
    
    cursor.execute('SELECT * FROM appointments ORDER BY created_at DESC LIMIT 10')
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"Booking ID:  {row['booking_id']}")
            print(f"Patient:     {row['patient_name']}")
            print(f"User ID:     {row['user_id']}")
            print(f"Department:  {row['department_name']} ({row['department']})")
            print(f"Doctor:      {row['doctor']}")
            print(f"Date:        {row['date']}")
            print(f"Time:        {row['time']}")
            print(f"Status:      {row['status']}")
            created = datetime.fromtimestamp(row['created_at']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Created:     {created}")
            print("-" * 70)
    else:
        print("No appointments found")
    
    # Count total
    cursor.execute('SELECT COUNT(*) FROM appointments')
    count = cursor.fetchone()[0]
    print(f"\nTotal appointments: {count}")
    
    conn.close()

if __name__ == "__main__":
    view_appointments()
