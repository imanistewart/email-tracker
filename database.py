import sqlite3
import logging
from datetime import datetime

DATABASE_FILE = "tracker.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table to store information about each email sent
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tracked_emails (
        tracking_id TEXT PRIMARY KEY,
        recipient TEXT NOT NULL,
        subject TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table to log each open event
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS open_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT NOT NULL,
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (tracking_id) REFERENCES tracked_emails (tracking_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

def log_open_event(tracking_id, ip_address, user_agent):
    """Logs an email open event to the database."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO open_events (tracking_id, ip_address, user_agent) VALUES (?, ?, ?)",
        (tracking_id, ip_address, user_agent)
    )
    conn.commit()
    conn.close()