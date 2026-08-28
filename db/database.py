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
    FOREIGN KEY (technician_id) REFERENCES technicians(id),
    UNIQUE (technician_id, start_time)
)
""")

connection.commit()
connection.close()
