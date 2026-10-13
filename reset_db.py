"""
Database Reset Script
WARNING: This will DELETE ALL DATA and create a fresh database.

Run: python reset_db.py
"""

import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_FILE = 'clinic_bot.db'


def reset_database():
    """Delete existing database and let init_database create a fresh one."""
    
    print("=" * 60)
    print("DATABASE RESET TOOL")
    print("=" * 60)
    print()
    print(f"This will DELETE the database file: {DATABASE_FILE}")
    print("All data will be PERMANENTLY LOST!")
    print()
    
    confirm = input("Type 'YES' to confirm deletion: ").strip()
    
    if confirm != 'YES':
        print("Cancelled. No changes made.")
        return
    
    # Delete the database file
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print(f"Deleted: {DATABASE_FILE}")
    else:
        print(f"Database file not found: {DATABASE_FILE}")
    
    # Re-initialize
    print("Re-initializing database...")
    from database import init_database
    init_database()
    
    print()
    print("=" * 60)
    print("Database reset complete!")
    print("A fresh database has been created.")
    print("=" * 60)


if __name__ == '__main__':
    reset_database()
