import sqlite3

import database  # noqa: F401  (ensures technicians/appointments tables exist)

TECHNICIANS = [
    (1, "Marcus Bennett", "County Alpha"),
    (2, "Sarah Coleman", "County Alpha"),
    (3, "David Nguyen", "County Alpha"),
    (4, "Angela Torres", "County Alpha"),
    (5, "James Whitfield", "County Alpha"),
    (6, "Priya Sharma", "County Alpha"),
    (7, "Kevin O'Brien", "County Alpha"),
    (8, "Rachel Kim", "County Alpha"),
    (9, "Daniel Foster", "County Alpha"),
    (10, "Michelle Alvarez", "County Alpha"),
    (11, "Brian Sutton", "County Alpha"),
    (12, "Laura Chen", "County Alpha"),
    (13, "Anthony Reyes", "County Alpha"),
    (14, "Nicole Hayes", "County Alpha"),
    (15, "Christopher Doyle", "County Bravo"),
    (16, "Emily Watson", "County Bravo"),
    (17, "Jason Park", "County Bravo"),
    (18, "Samantha Reed", "County Bravo"),
    (19, "Matthew Ellis", "County Bravo"),
    (20, "Victoria Cruz", "County Bravo"),
    (21, "Ryan Mitchell", "County Bravo"),
    (22, "Olivia Grant", "County Bravo"),
    (23, "Tyler Brooks", "County Bravo"),
    (24, "Hannah Price", "County Bravo"),
    (25, "Justin Marsh", "County Bravo"),
    (26, "Grace Palmer", "County Bravo"),
    (27, "Nathan Ortiz", "County Bravo"),
    (28, "Benjamin Ross", "County Charlie"),
    (29, "Sophia Delgado", "County Charlie"),
    (30, "Andrew Wallace", "County Charlie"),
    (31, "Isabella Cortez", "County Charlie"),
    (32, "Jonathan Pierce", "County Charlie"),
    (33, "Megan Fuller", "County Charlie"),
    (34, "Eric Sandoval", "County Charlie"),
    (35, "Chloe Bennett", "County Charlie"),
    (36, "Timothy Ward", "County Charlie"),
    (37, "Amanda Vega", "County Charlie"),
    (38, "Patrick Dunn", "County Charlie"),
    (39, "Jessica Moreno", "County Charlie"),
    (40, "Gregory Lane", "County Charlie"),
]

connection = sqlite3.connect("summit_air.db")

# Delete all appointments and technicians
connection.execute("DELETE FROM appointments")
connection.execute("DELETE FROM technicians")

connection.executemany(
    "INSERT INTO technicians (id, name, county) VALUES (?, ?, ?)",
    TECHNICIANS,
)

connection.commit()

total = connection.execute("SELECT COUNT(*) FROM technicians").fetchone()[0]
alpha = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", ("County Alpha",)
).fetchone()[0]
bravo = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", ("County Bravo",)
).fetchone()[0]
charlie = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", ("County Charlie",)
).fetchone()[0]
appointments = connection.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]

assert total == 40, f"expected 40 technicians, found {total}"
assert alpha == 14, f"expected 14 technicians in County Alpha, found {alpha}"
assert bravo == 13, f"expected 13 technicians in County Bravo, found {bravo}"
assert charlie == 13, f"expected 13 technicians in County Charlie, found {charlie}"
assert appointments == 0, f"expected 0 appointments after reset, found {appointments}"

print("Reset complete: 40 technicians (14 Alpha, 13 Bravo, 13 Charlie), 0 appointments.")

connection.close()
