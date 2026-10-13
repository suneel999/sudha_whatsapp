
import sqlite3
conn = sqlite3.connect('clinic_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT user_id, source FROM appointments WHERE booking_id LIKE "APT_%_TEST"')
results = cursor.fetchall()
for row in results:
    print(f"User ID: {row[0]}, Source: {row[1]}")
conn.close()
