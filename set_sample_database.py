import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

import reset_database  # noqa: F401  (wipes + reseeds technicians, clears appointments)
from config import (
    BUSINESS_DAYS,
    BUSINESS_END_HOUR,
    BUSINESS_START_HOUR,
    BUFFER_MINUTES,
    APPOINTMENT_DURATION_MINUTES,
    COUNTIES,
    Priority,
)

# Static, hand-verified set of 67 appointments across the 40 technicians.
# Columns: id, technician_id, customer_name, customer_phone, customer_address,
#          county, issue, priority, start_time, end_time
APPOINTMENTS = [
    (1, 1, 'Robert Harris', '555-100-1000', '100 Maple Ave, Alphaton', 'County Alpha', 'AC not cooling', 'routine', '2026-08-27T08:00:00', '2026-08-27T08:30:00'),
    (2, 4, 'Linda Clark', '555-101-1001', '101 Oak St, Alphaton', 'County Alpha', "Furnace won't ignite", 'routine', '2026-08-28T08:30:00', '2026-08-28T09:00:00'),
    (3, 8, 'William Lewis', '555-102-1002', '102 Cedar Ln, Alphaton', 'County Alpha', 'Thermostat not responding', 'routine', '2026-08-31T09:00:00', '2026-08-31T09:30:00'),
    (4, 12, 'Karen Walker', '555-103-1003', '103 Birch Rd, Alphaton', 'County Alpha', 'Refrigerant leak', 'urgent', '2026-09-01T09:30:00', '2026-09-01T10:00:00'),
    (5, 15, 'Thomas Young', '555-104-1004', '104 Pine Dr, Bravoville', 'County Bravo', 'Strange grinding noise from unit', 'routine', '2026-09-02T10:00:00', '2026-09-02T10:30:00'),
    (6, 18, 'Susan Allen', '555-105-1005', '105 Elm St, Bravoville', 'County Bravo', 'No airflow from vents', 'routine', '2026-09-03T10:30:00', '2026-09-03T11:00:00'),
    (7, 21, 'Charles King', '555-106-1006', '106 Willow Way, Bravoville', 'County Bravo', 'Water leaking near indoor unit', 'urgent', '2026-09-04T11:00:00', '2026-09-04T11:30:00'),
    (8, 24, 'Nancy Wright', '555-107-1007', '107 Chestnut Ct, Bravoville', 'County Bravo', 'Heat pump not heating', 'emergency', '2026-09-07T11:30:00', '2026-09-07T12:00:00'),
    (9, 28, 'Joseph Scott', '555-108-1008', '108 Walnut Blvd, Charleston Falls', 'County Charlie', 'Circuit breaker trips repeatedly', 'routine', '2026-09-08T12:00:00', '2026-09-08T12:30:00'),
    (10, 31, 'Betty Green', '555-109-1009', '109 Spruce Cir, Charleston Falls', 'County Charlie', 'Compressor short cycling', 'routine', '2026-09-09T12:30:00', '2026-09-09T13:00:00'),
    (11, 34, 'Christopher Baker', '555-110-1010', '110 Aspen Trl, Charleston Falls', 'County Charlie', 'Blower motor not running', 'routine', '2026-08-27T13:00:00', '2026-08-27T13:30:00'),
    (12, 37, 'Sandra Adams', '555-111-1011', '111 Magnolia St, Charleston Falls', 'County Charlie', 'Annual maintenance inspection', 'urgent', '2026-08-28T13:30:00', '2026-08-28T14:00:00'),
    (13, 40, 'Daniel Nelson', '555-112-1012', '112 Sycamore Dr, Charleston Falls', 'County Charlie', 'Air filter replacement', 'routine', '2026-08-31T14:00:00', '2026-08-31T14:30:00'),
    (14, 9, 'Ashley Hill', '555-113-1013', '113 Poplar Ave, Alphaton', 'County Alpha', 'Ignitor failure on furnace', 'routine', '2026-09-01T14:30:00', '2026-09-01T15:00:00'),
    (15, 9, 'Paul Ramirez', '555-114-1014', '114 Hickory Ln, Alphaton', 'County Alpha', 'Condenser coil frozen', 'urgent', '2026-09-01T15:30:00', '2026-09-01T16:00:00'),
    (16, 10, 'Kimberly Campbell', '555-115-1015', '115 Maple Ave, Alphaton', 'County Alpha', 'Uneven cooling between rooms', 'emergency', '2026-09-02T15:00:00', '2026-09-02T15:30:00'),
    (17, 10, 'Mark Mitchell', '555-116-1016', '116 Oak St, Alphaton', 'County Alpha', 'Ductwork noise / rattling', 'routine', '2026-09-02T16:00:00', '2026-09-02T16:30:00'),
    (18, 11, 'Donna Roberts', '555-117-1017', '117 Cedar Ln, Alphaton', 'County Alpha', 'Outdoor unit not turning on', 'routine', '2026-09-03T15:30:00', '2026-09-03T16:00:00'),
    (19, 11, 'George Carter', '555-118-1018', '118 Birch Rd, Alphaton', 'County Alpha', 'AC not cooling', 'routine', '2026-09-03T16:30:00', '2026-09-03T17:00:00'),
    (20, 13, 'Carol Phillips', '555-119-1019', '119 Pine Dr, Alphaton', 'County Alpha', "Furnace won't ignite", 'urgent', '2026-09-04T08:00:00', '2026-09-04T08:30:00'),
    (21, 13, 'Steven Evans', '555-120-1020', '120 Elm St, Alphaton', 'County Alpha', 'Thermostat not responding', 'routine', '2026-09-04T09:00:00', '2026-09-04T09:30:00'),
    (22, 14, 'Ruth Turner', '555-121-1021', '121 Willow Way, Alphaton', 'County Alpha', 'Refrigerant leak', 'routine', '2026-09-07T08:30:00', '2026-09-07T09:00:00'),
    (23, 14, 'Edward Parker', '555-122-1022', '122 Chestnut Ct, Alphaton', 'County Alpha', 'Strange grinding noise from unit', 'urgent', '2026-09-07T09:30:00', '2026-09-07T10:00:00'),
    (24, 16, 'Sharon Collins', '555-123-1023', '123 Walnut Blvd, Bravoville', 'County Bravo', 'No airflow from vents', 'emergency', '2026-09-08T09:00:00', '2026-09-08T09:30:00'),
    (25, 16, 'Brian Edwards', '555-124-1024', '124 Spruce Cir, Bravoville', 'County Bravo', 'Water leaking near indoor unit', 'routine', '2026-09-08T10:00:00', '2026-09-08T10:30:00'),
    (26, 17, 'Michelle Stewart', '555-125-1025', '125 Aspen Trl, Bravoville', 'County Bravo', 'Heat pump not heating', 'routine', '2026-09-09T09:30:00', '2026-09-09T10:00:00'),
    (27, 17, 'Ronald Morris', '555-126-1026', '126 Magnolia St, Bravoville', 'County Bravo', 'Circuit breaker trips repeatedly', 'routine', '2026-09-09T10:30:00', '2026-09-09T11:00:00'),
    (28, 19, 'Laura Rogers', '555-127-1027', '127 Sycamore Dr, Bravoville', 'County Bravo', 'Compressor short cycling', 'urgent', '2026-08-27T10:00:00', '2026-08-27T10:30:00'),
    (29, 19, 'Anthony Cook', '555-128-1028', '128 Poplar Ave, Bravoville', 'County Bravo', 'Blower motor not running', 'routine', '2026-08-27T11:00:00', '2026-08-27T11:30:00'),
    (30, 20, 'Sarah Bell', '555-129-1029', '129 Hickory Ln, Bravoville', 'County Bravo', 'Annual maintenance inspection', 'routine', '2026-08-28T10:30:00', '2026-08-28T11:00:00'),
    (31, 20, 'Kevin Murphy', '555-130-1030', '130 Maple Ave, Bravoville', 'County Bravo', 'Air filter replacement', 'urgent', '2026-08-28T11:30:00', '2026-08-28T12:00:00'),
    (32, 22, 'Deborah Bailey', '555-131-1031', '131 Oak St, Bravoville', 'County Bravo', 'Ignitor failure on furnace', 'emergency', '2026-08-31T11:00:00', '2026-08-31T11:30:00'),
    (33, 22, 'Jason Rivera', '555-132-1032', '132 Cedar Ln, Bravoville', 'County Bravo', 'Condenser coil frozen', 'routine', '2026-08-31T12:00:00', '2026-08-31T12:30:00'),
    (34, 23, 'Amy Cooper', '555-133-1033', '133 Birch Rd, Bravoville', 'County Bravo', 'Uneven cooling between rooms', 'routine', '2026-09-01T11:30:00', '2026-09-01T12:00:00'),
    (35, 23, 'Jeffrey Richardson', '555-134-1034', '134 Pine Dr, Bravoville', 'County Bravo', 'Ductwork noise / rattling', 'routine', '2026-09-01T12:30:00', '2026-09-01T13:00:00'),
    (36, 25, 'Angela Cox', '555-135-1035', '135 Elm St, Bravoville', 'County Bravo', 'Outdoor unit not turning on', 'urgent', '2026-09-02T12:00:00', '2026-09-02T12:30:00'),
    (37, 25, 'Ryan Howard', '555-136-1036', '136 Willow Way, Bravoville', 'County Bravo', 'AC not cooling', 'routine', '2026-09-02T13:00:00', '2026-09-02T13:30:00'),
    (38, 26, 'Melissa Ward', '555-137-1037', '137 Chestnut Ct, Bravoville', 'County Bravo', "Furnace won't ignite", 'routine', '2026-09-03T12:30:00', '2026-09-03T13:00:00'),
    (39, 26, 'Jacob Peterson', '555-138-1038', '138 Walnut Blvd, Bravoville', 'County Bravo', 'Thermostat not responding', 'urgent', '2026-09-03T13:30:00', '2026-09-03T14:00:00'),
    (40, 27, 'Rebecca Gray', '555-139-1039', '139 Spruce Cir, Bravoville', 'County Bravo', 'Refrigerant leak', 'emergency', '2026-09-04T13:00:00', '2026-09-04T13:30:00'),
    (41, 27, 'Gary Ramsey', '555-140-1040', '140 Aspen Trl, Bravoville', 'County Bravo', 'Strange grinding noise from unit', 'routine', '2026-09-04T14:00:00', '2026-09-04T14:30:00'),
    (42, 29, 'Cynthia James', '555-141-1041', '141 Magnolia St, Charleston Falls', 'County Charlie', 'No airflow from vents', 'routine', '2026-09-07T13:30:00', '2026-09-07T14:00:00'),
    (43, 29, 'Nicholas Watson', '555-142-1042', '142 Sycamore Dr, Charleston Falls', 'County Charlie', 'Water leaking near indoor unit', 'routine', '2026-09-07T14:30:00', '2026-09-07T15:00:00'),
    (44, 30, 'Kathleen Brooks', '555-143-1043', '143 Poplar Ave, Charleston Falls', 'County Charlie', 'Heat pump not heating', 'urgent', '2026-09-08T14:00:00', '2026-09-08T14:30:00'),
    (45, 30, 'Eric Kelly', '555-144-1044', '144 Hickory Ln, Charleston Falls', 'County Charlie', 'Circuit breaker trips repeatedly', 'routine', '2026-09-08T15:00:00', '2026-09-08T15:30:00'),
    (46, 32, 'Amanda Sanders', '555-145-1045', '145 Maple Ave, Charleston Falls', 'County Charlie', 'Compressor short cycling', 'routine', '2026-09-09T14:30:00', '2026-09-09T15:00:00'),
    (47, 32, 'Stephen Price', '555-146-1046', '146 Oak St, Charleston Falls', 'County Charlie', 'Blower motor not running', 'urgent', '2026-09-09T15:30:00', '2026-09-09T16:00:00'),
    (48, 33, 'Shirley Bennett', '555-147-1047', '147 Cedar Ln, Charleston Falls', 'County Charlie', 'Annual maintenance inspection', 'emergency', '2026-08-27T15:00:00', '2026-08-27T15:30:00'),
    (49, 33, 'Jonathan Wood', '555-148-1048', '148 Birch Rd, Charleston Falls', 'County Charlie', 'Air filter replacement', 'routine', '2026-08-27T16:00:00', '2026-08-27T16:30:00'),
    (50, 35, 'Anna Barnes', '555-149-1049', '149 Pine Dr, Charleston Falls', 'County Charlie', 'Ignitor failure on furnace', 'routine', '2026-08-28T15:30:00', '2026-08-28T16:00:00'),
    (51, 35, 'Larry Ross', '555-150-1050', '150 Elm St, Charleston Falls', 'County Charlie', 'Condenser coil frozen', 'routine', '2026-08-28T16:30:00', '2026-08-28T17:00:00'),
    (52, 36, 'Brenda Henderson', '555-151-1051', '151 Willow Way, Charleston Falls', 'County Charlie', 'Uneven cooling between rooms', 'urgent', '2026-08-31T08:00:00', '2026-08-31T08:30:00'),
    (53, 36, 'Justin Coleman', '555-152-1052', '152 Chestnut Ct, Charleston Falls', 'County Charlie', 'Ductwork noise / rattling', 'routine', '2026-08-31T09:00:00', '2026-08-31T09:30:00'),
    (54, 38, 'Emma Jenkins', '555-153-1053', '153 Walnut Blvd, Charleston Falls', 'County Charlie', 'Outdoor unit not turning on', 'routine', '2026-09-01T08:30:00', '2026-09-01T09:00:00'),
    (55, 38, 'Scott Perry', '555-154-1054', '154 Spruce Cir, Charleston Falls', 'County Charlie', 'AC not cooling', 'urgent', '2026-09-01T09:30:00', '2026-09-01T10:00:00'),
    (56, 39, 'Pamela Powell', '555-155-1055', '155 Aspen Trl, Charleston Falls', 'County Charlie', "Furnace won't ignite", 'emergency', '2026-09-02T09:00:00', '2026-09-02T09:30:00'),
    (57, 39, 'Brandon Long', '555-156-1056', '156 Magnolia St, Charleston Falls', 'County Charlie', 'Thermostat not responding', 'routine', '2026-09-02T10:00:00', '2026-09-02T10:30:00'),
    (58, 2, 'Nicole Patterson', '555-157-1057', '157 Sycamore Dr, Alphaton', 'County Alpha', 'Refrigerant leak', 'routine', '2026-09-03T08:30:00', '2026-09-03T09:00:00'),
    (59, 2, 'Frank Hughes', '555-158-1058', '158 Poplar Ave, Alphaton', 'County Alpha', 'Strange grinding noise from unit', 'routine', '2026-09-03T09:00:00', '2026-09-03T09:30:00'),
    (60, 3, 'Samantha Flores', '555-159-1059', '159 Hickory Ln, Alphaton', 'County Alpha', 'No airflow from vents', 'urgent', '2026-09-04T09:00:00', '2026-09-04T09:30:00'),
    (61, 3, 'Benjamin Washington', '555-160-1060', '160 Maple Ave, Alphaton', 'County Alpha', 'Water leaking near indoor unit', 'routine', '2026-09-04T09:30:00', '2026-09-04T10:00:00'),
    (62, 5, 'Katherine Butler', '555-161-1061', '161 Oak St, Alphaton', 'County Alpha', 'Heat pump not heating', 'routine', '2026-09-07T09:30:00', '2026-09-07T10:00:00'),
    (63, 5, 'Gregory Simmons', '555-162-1062', '162 Cedar Ln, Alphaton', 'County Alpha', 'Circuit breaker trips repeatedly', 'urgent', '2026-09-07T10:00:00', '2026-09-07T10:30:00'),
    (64, 6, 'Christine Foster', '555-163-1063', '163 Birch Rd, Alphaton', 'County Alpha', 'Compressor short cycling', 'emergency', '2026-09-08T10:00:00', '2026-09-08T10:30:00'),
    (65, 6, 'Raymond Gonzales', '555-164-1064', '164 Pine Dr, Alphaton', 'County Alpha', 'Blower motor not running', 'routine', '2026-09-08T10:30:00', '2026-09-08T11:00:00'),
    (66, 7, 'Debra Bryant', '555-165-1065', '165 Elm St, Alphaton', 'County Alpha', 'Annual maintenance inspection', 'routine', '2026-09-09T10:30:00', '2026-09-09T11:00:00'),
    (67, 7, 'Samuel Alexander', '555-166-1066', '166 Willow Way, Alphaton', 'County Alpha', 'Air filter replacement', 'routine', '2026-09-09T11:00:00', '2026-09-09T11:30:00'),
]

assert len(APPOINTMENTS) == 67, "APPOINTMENTS must contain exactly 67 rows"

connection = sqlite3.connect("summit_air.db")

connection.executemany(
    """
    INSERT INTO appointments (
        id, technician_id, customer_name, customer_phone, customer_address,
        county, issue, priority, start_time, end_time
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    APPOINTMENTS,
)
connection.commit()

# --- assertions: confirm the seed data actually landed in the DB correctly ---

technician_county = {
    row[0]: row[1]
    for row in connection.execute("SELECT id, county FROM technicians")
}
assert len(technician_county) == 40, (
    f"expected 40 technicians in the database, found {len(technician_county)}"
)

rows = connection.execute(
    """
    SELECT id, technician_id, customer_name, customer_phone, customer_address,
           county, issue, priority, start_time, end_time
    FROM appointments
    ORDER BY id
    """
).fetchall()

assert len(rows) == 67, f"expected 67 appointments in the database, found {len(rows)}"
assert [row[0] for row in rows] == list(range(1, 68)), (
    "appointment ids are not exactly 1..67"
)

valid_priorities = {p.value for p in Priority}
by_tech_day = defaultdict(list)

for row in rows:
    (appt_id, technician_id, customer_name, customer_phone, customer_address,
     county, issue, priority, start_time, end_time) = row

    assert technician_id in technician_county, (
        f"appointment {appt_id} references unknown technician_id {technician_id}"
    )
    assert county == technician_county[technician_id], (
        f"appointment {appt_id} county {county!r} does not match "
        f"technician {technician_id}'s county {technician_county[technician_id]!r}"
    )
    assert county in COUNTIES, f"appointment {appt_id} has invalid county {county!r}"
    assert priority in valid_priorities, (
        f"appointment {appt_id} has invalid priority {priority!r}"
    )
    assert customer_name and customer_phone and customer_address and issue, (
        f"appointment {appt_id} is missing a required text field"
    )

    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    assert start_dt.weekday() in BUSINESS_DAYS, (
        f"appointment {appt_id} starts on a non-business day: {start_time}"
    )
    assert (start_dt.hour, start_dt.minute) >= (BUSINESS_START_HOUR, 0), (
        f"appointment {appt_id} starts before business hours: {start_time}"
    )
    assert (end_dt.hour, end_dt.minute) <= (BUSINESS_END_HOUR, 0), (
        f"appointment {appt_id} ends after business hours: {end_time}"
    )
    assert end_dt - start_dt == timedelta(minutes=APPOINTMENT_DURATION_MINUTES), (
        f"appointment {appt_id} duration is not {APPOINTMENT_DURATION_MINUTES} minutes"
    )

    by_tech_day[(technician_id, start_time[:10])].append((start_dt, end_dt))

buffered_pairs = 0
zero_gap_pairs = 0
for (technician_id, day), times in by_tech_day.items():
    times.sort()
    for (_, prev_end), (next_start, _) in zip(times, times[1:]):
        gap_minutes = (next_start - prev_end).total_seconds() / 60
        assert gap_minutes >= 0, (
            f"technician {technician_id} has overlapping appointments on {day}"
        )
        if gap_minutes == 0:
            zero_gap_pairs += 1
        else:
            assert gap_minutes >= BUFFER_MINUTES, (
                f"technician {technician_id} has a same-day gap of {gap_minutes} "
                f"minutes on {day}, which is less than the {BUFFER_MINUTES}-minute buffer"
            )
            buffered_pairs += 1

assert buffered_pairs > 0, "expected at least one buffered same-day appointment pair"
assert zero_gap_pairs > 0, "expected at least one back-to-back (no buffer) appointment pair"

print(f"Total appointments: {len(rows)}")
print(f"Buffered same-day pairs: {buffered_pairs}")
print(f"Back-to-back (no buffer) same-day pairs: {zero_gap_pairs}")
print("All seed data assertions passed.")

connection.close()
