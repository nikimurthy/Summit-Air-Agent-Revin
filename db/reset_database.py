import sqlite3

import db.database as database  # noqa: F401  (ensures technicians/appointments tables exist)
from config import County

#input 40 arbitrary technicians split among 3 counties
TECHNICIANS = [
    (1, "Marcus Bennett", County.ALPHA),
    (2, "Sarah Coleman", County.ALPHA),
    (3, "David Nguyen", County.ALPHA),
    (4, "Angela Torres", County.ALPHA),
    (5, "James Whitfield", County.ALPHA),
    (6, "Priya Sharma", County.ALPHA),
    (7, "Kevin O'Brien", County.ALPHA),
    (8, "Rachel Kim", County.ALPHA),
    (9, "Daniel Foster", County.ALPHA),
    (10, "Michelle Alvarez", County.ALPHA),
    (11, "Brian Sutton", County.ALPHA),
    (12, "Laura Chen", County.ALPHA),
    (13, "Anthony Reyes", County.ALPHA),
    (14, "Nicole Hayes", County.ALPHA),
    (15, "Christopher Doyle", County.BRAVO),
    (16, "Emily Watson", County.BRAVO),
    (17, "Jason Park", County.BRAVO),
    (18, "Samantha Reed", County.BRAVO),
    (19, "Matthew Ellis", County.BRAVO),
    (20, "Victoria Cruz", County.BRAVO),
    (21, "Ryan Mitchell", County.BRAVO),
    (22, "Olivia Grant", County.BRAVO),
    (23, "Tyler Brooks", County.BRAVO),
    (24, "Hannah Price", County.BRAVO),
    (25, "Justin Marsh", County.BRAVO),
    (26, "Grace Palmer", County.BRAVO),
    (27, "Nathan Ortiz", County.BRAVO),
    (28, "Benjamin Ross", County.CHARLIE),
    (29, "Sophia Delgado", County.CHARLIE),
    (30, "Andrew Wallace", County.CHARLIE),
    (31, "Isabella Cortez", County.CHARLIE),
    (32, "Jonathan Pierce", County.CHARLIE),
    (33, "Megan Fuller", County.CHARLIE),
    (34, "Eric Sandoval", County.CHARLIE),
    (35, "Chloe Bennett", County.CHARLIE),
    (36, "Timothy Ward", County.CHARLIE),
    (37, "Amanda Vega", County.CHARLIE),
    (38, "Patrick Dunn", County.CHARLIE),
    (39, "Jessica Moreno", County.CHARLIE),
    (40, "Gregory Lane", County.CHARLIE),
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

# testing below
total = connection.execute("SELECT COUNT(*) FROM technicians").fetchone()[0]
alpha = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", (County.ALPHA,)
).fetchone()[0]
bravo = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", (County.BRAVO,)
).fetchone()[0]
charlie = connection.execute(
    "SELECT COUNT(*) FROM technicians WHERE county = ?", (County.CHARLIE,)
).fetchone()[0]
appointments = connection.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]

assert total == 40, f"expected 40 technicians, found {total}"
assert alpha == 14, f"expected 14 technicians in County Alpha, found {alpha}"
assert bravo == 13, f"expected 13 technicians in County Bravo, found {bravo}"
assert charlie == 13, f"expected 13 technicians in County Charlie, found {charlie}"
assert appointments == 0, f"expected 0 appointments after reset, found {appointments}"

print("Reset complete: 40 technicians (14 Alpha, 13 Bravo, 13 Charlie), 0 appointments.")

connection.close()
