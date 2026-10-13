"""
Database Migration Script - Production Ready
Run this script to upgrade existing database schema to the latest version.

Usage: python migrate_db.py

This script is safe to run multiple times - it only adds columns if they don't exist.
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_FILE = 'clinic_bot.db'


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    """Run all migrations."""
    logger.info("Starting database migration...")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    migrations_run = 0
    
    # ============ APPOINTMENTS TABLE MIGRATIONS ============
    
    # Add source column
    if not column_exists(cursor, 'appointments', 'source'):
        cursor.execute("ALTER TABLE appointments ADD COLUMN source TEXT DEFAULT 'whatsapp'")
        logger.info("Added 'source' column to appointments")
        migrations_run += 1
    
    # Add notes column
    if not column_exists(cursor, 'appointments', 'notes'):
        cursor.execute("ALTER TABLE appointments ADD COLUMN notes TEXT")
        logger.info("Added 'notes' column to appointments")
        migrations_run += 1
    
    # Add updated_at column
    if not column_exists(cursor, 'appointments', 'updated_at'):
        cursor.execute("ALTER TABLE appointments ADD COLUMN updated_at REAL")
        logger.info("Added 'updated_at' column to appointments")
        migrations_run += 1
    
    # ============ DIAGNOSTICS TABLE MIGRATIONS ============
    
    # Add clinic_id column
    if not column_exists(cursor, 'diagnostics', 'clinic_id'):
        cursor.execute("ALTER TABLE diagnostics ADD COLUMN clinic_id TEXT DEFAULT 'default'")
        logger.info("Added 'clinic_id' column to diagnostics")
        migrations_run += 1
    
    # Add source column
    if not column_exists(cursor, 'diagnostics', 'source'):
        cursor.execute("ALTER TABLE diagnostics ADD COLUMN source TEXT DEFAULT 'whatsapp'")
        logger.info("Added 'source' column to diagnostics")
        migrations_run += 1
    
    # Add notes column
    if not column_exists(cursor, 'diagnostics', 'notes'):
        cursor.execute("ALTER TABLE diagnostics ADD COLUMN notes TEXT")
        logger.info("Added 'notes' column to diagnostics")
        migrations_run += 1
    
    # Add updated_at column
    if not column_exists(cursor, 'diagnostics', 'updated_at'):
        cursor.execute("ALTER TABLE diagnostics ADD COLUMN updated_at REAL")
        logger.info("Added 'updated_at' column to diagnostics")
        migrations_run += 1
    
    # ============ ADMISSIONS TABLE MIGRATIONS ============
    
    # Add phone column
    if not column_exists(cursor, 'admissions', 'phone'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN phone TEXT")
        logger.info("Added 'phone' column to admissions")
        migrations_run += 1
    
    # Add preferred_date column
    if not column_exists(cursor, 'admissions', 'preferred_date'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN preferred_date TEXT")
        logger.info("Added 'preferred_date' column to admissions")
        migrations_run += 1
    
    # Add clinic_id column
    if not column_exists(cursor, 'admissions', 'clinic_id'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN clinic_id TEXT DEFAULT 'default'")
        logger.info("Added 'clinic_id' column to admissions")
        migrations_run += 1
    
    # Add source column
    if not column_exists(cursor, 'admissions', 'source'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN source TEXT DEFAULT 'whatsapp'")
        logger.info("Added 'source' column to admissions")
        migrations_run += 1
    
    # Add notes column
    if not column_exists(cursor, 'admissions', 'notes'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN notes TEXT")
        logger.info("Added 'notes' column to admissions")
        migrations_run += 1
    
    # Add updated_at column
    if not column_exists(cursor, 'admissions', 'updated_at'):
        cursor.execute("ALTER TABLE admissions ADD COLUMN updated_at REAL")
        logger.info("Added 'updated_at' column to admissions")
        migrations_run += 1
    
    # ============ PATIENTS TABLE MIGRATIONS ============
    
    # Rename total_bookings to total_appointments if needed
    if column_exists(cursor, 'patients', 'total_bookings') and not column_exists(cursor, 'patients', 'total_appointments'):
        # SQLite doesn't support column rename directly in older versions
        # We'll add new columns instead
        cursor.execute("ALTER TABLE patients ADD COLUMN total_appointments INTEGER DEFAULT 0")
        cursor.execute("UPDATE patients SET total_appointments = total_bookings")
        logger.info("Added 'total_appointments' column to patients")
        migrations_run += 1
    
    # Add total_appointments if doesn't exist
    if not column_exists(cursor, 'patients', 'total_appointments'):
        cursor.execute("ALTER TABLE patients ADD COLUMN total_appointments INTEGER DEFAULT 0")
        logger.info("Added 'total_appointments' column to patients")
        migrations_run += 1
    
    # Add total_diagnostics column
    if not column_exists(cursor, 'patients', 'total_diagnostics'):
        cursor.execute("ALTER TABLE patients ADD COLUMN total_diagnostics INTEGER DEFAULT 0")
        logger.info("Added 'total_diagnostics' column to patients")
        migrations_run += 1
    
    # Add total_admissions column
    if not column_exists(cursor, 'patients', 'total_admissions'):
        cursor.execute("ALTER TABLE patients ADD COLUMN total_admissions INTEGER DEFAULT 0")
        logger.info("Added 'total_admissions' column to patients")
        migrations_run += 1
    
    # Add tags column
    if not column_exists(cursor, 'patients', 'tags'):
        cursor.execute("ALTER TABLE patients ADD COLUMN tags TEXT")
        logger.info("Added 'tags' column to patients")
        migrations_run += 1
    
    # ============ INTERACTIONS TABLE MIGRATIONS ============
    
    # Add user_id column
    if not column_exists(cursor, 'interactions', 'user_id'):
        cursor.execute("ALTER TABLE interactions ADD COLUMN user_id TEXT")
        logger.info("Added 'user_id' column to interactions")
        migrations_run += 1
    
    # Add message_type column
    if not column_exists(cursor, 'interactions', 'message_type'):
        cursor.execute("ALTER TABLE interactions ADD COLUMN message_type TEXT DEFAULT 'text'")
        logger.info("Added 'message_type' column to interactions")
        migrations_run += 1
    
    # Add payload column
    if not column_exists(cursor, 'interactions', 'payload'):
        cursor.execute("ALTER TABLE interactions ADD COLUMN payload TEXT")
        logger.info("Added 'payload' column to interactions")
        migrations_run += 1
    
    # ============ CREATE INDEXES ============
    
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(phone)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diagnostics_user ON diagnostics(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diagnostics_date ON diagnostics(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_diagnostics_phone ON diagnostics(phone)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admissions_user ON admissions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admissions_date ON admissions(preferred_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admissions_phone ON admissions(phone)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_external ON patients(external_id)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_patient ON interactions(patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_time ON interactions(timestamp)')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_state_user ON conversation_state(user_id)')
        
        logger.info("Indexes created/verified")
    except Exception as e:
        logger.warning(f"Index creation warning (may already exist): {e}")
    
    # Commit all changes
    conn.commit()
    conn.close()
    
    if migrations_run > 0:
        logger.info(f"Migration complete! {migrations_run} changes applied.")
    else:
        logger.info("Database already up to date. No migrations needed.")


def verify_schema():
    """Verify the database schema is correct."""
    logger.info("Verifying database schema...")
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Check all required tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'appointments', 'diagnostics', 'admissions', 
        'patients', 'interactions', 'conversation_state', 
        'sessions', 'ai_interactions'
    ]
    
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        logger.error(f"Missing tables: {missing}")
        logger.info("Run the application once to create all tables, then run this script again.")
        return False
    
    logger.info("All required tables exist.")
    
    # Check key columns in each table
    checks = [
        ('appointments', ['booking_id', 'user_id', 'patient_name', 'phone', 'doctor', 'date', 'time']),
        ('diagnostics', ['booking_id', 'user_id', 'patient_name', 'phone', 'test_type', 'date', 'time']),
        ('admissions', ['admission_id', 'user_id', 'patient_name', 'phone', 'preferred_date', 'admission_type']),
        ('patients', ['external_id', 'platform', 'name', 'phone', 'total_appointments', 'total_diagnostics']),
    ]
    
    all_ok = True
    for table, columns in checks:
        for col in columns:
            if not column_exists(cursor, table, col):
                logger.error(f"Missing column: {table}.{col}")
                all_ok = False
    
    conn.close()
    
    if all_ok:
        logger.info("Schema verification complete. All columns present.")
    
    return all_ok


if __name__ == '__main__':
    print("=" * 60)
    print("Mallika Hospitals - Database Migration Tool")
    print("=" * 60)
    print()
    
    migrate()
    print()
    verify_schema()
    
    print()
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
