"""
Sets up the database file the first time the app runs, and fills it with
a few sample properties and applications so there's something to look at
right away. Safe to import and call every time the app starts — it only
creates the file/tables if they don't already exist, and only adds sample
data if the properties table is empty.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "app.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_database():
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()

    already_has_data = conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0] > 0
    if not already_has_data:
        _add_sample_data(conn)

    conn.close()


def _add_sample_data(conn):
    properties = [
        ("Maple Court Apartments", "123 Maple St, Springfield", "manager.maplecourt@example.com"),
        ("Riverside Commons", "456 River Rd, Springfield", "manager.riverside@example.com"),
        ("Oakwood Terrace", "789 Oak Ave, Springfield", "manager.oakwood@example.com"),
        ("Sunset Gardens", "321 Sunset Blvd, Springfield", "manager.sunsetgardens@example.com"),
        ("Birchwood Homes", "654 Birch Ln, Springfield", "manager.birchwood@example.com"),
    ]
    conn.executemany(
        "INSERT INTO properties (name, address, property_manager_email) VALUES (?, ?, ?)",
        properties,
    )
    conn.commit()

    property_ids = [row[0] for row in conn.execute("SELECT id FROM properties ORDER BY id").fetchall()]

    sample_applications = [
        # property_id,        full_name,       phone,           email,                    address,                   marital_status, children, status,     decision_date
        (property_ids[0], "Jordan Alvarez", "555-010-1234", "jordan.alvarez@example.com", "44 Elm St, Springfield", "Single", 0, "Pending", None),
        (property_ids[1], "Priya Natarajan", "555-010-5678", "priya.n@example.com", "89 Cedar Ave, Springfield", "Married", 2, "Approved", "2026-07-15"),
        (property_ids[2], "Marcus Webb", "555-010-9012", "marcus.webb@example.com", "17 Pine Rd, Springfield", "Divorced", 1, "Denied", "2026-07-20"),
    ]
    conn.executemany(
        """INSERT INTO applications
           (property_id, full_name, phone, email, current_address,
            marital_status, number_of_children, status, decision_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_applications,
    )
    conn.commit()

    # Matches the format the "Date and Time" field on the admin Inspection
    # Slots page produces (YYYY-MM-DDTHH:MM, 24-hour), so sample slots sort
    # correctly alongside slots added later through the app.
    sample_slots = [
        ("2026-08-05T10:00",),
        ("2026-08-05T14:00",),
        ("2026-08-06T09:30",),
    ]
    conn.executemany("INSERT INTO inspection_slots (slot_time) VALUES (?)", sample_slots)
    conn.commit()


if __name__ == "__main__":
    ensure_database()
    print("Database is ready at:", DB_PATH)
