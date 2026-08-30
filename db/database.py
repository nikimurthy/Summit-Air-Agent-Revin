import sqlite3

connection = sqlite3.connect("summit_air.db")

connection.execute("""
CREATE TABLE IF NOT EXISTS technicians (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    county TEXT NOT NULL
)
""")

connection.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    technician_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    customer_phone TEXT,
    customer_address TEXT NOT NULL,
    county TEXT NOT NULL,
    issue TEXT NOT NULL,
    priority TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    service_request_id INTEGER,
    FOREIGN KEY (technician_id) REFERENCES technicians(id),
    UNIQUE (technician_id, start_time)
)
""")

connection.execute("""
CREATE TABLE IF NOT EXISTS service_requests (
    request_id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    address TEXT,
    county TEXT,
    property_type TEXT,
    issue_description TEXT,
    priority TEXT,
    availability_raw TEXT,
    appointment_id INTEGER,
    booking_status TEXT,
    escalation_status TEXT,
    final_phase TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
)
""")

connection.commit()
connection.close()
