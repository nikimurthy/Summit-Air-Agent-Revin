import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional

from config import (
    BUSINESS_START_HOUR,
    BUSINESS_END_HOUR,
    BUSINESS_DAYS,
    APPOINTMENT_DURATION_MINUTES,
    BUFFER_MINUTES,
    County,
    PropertyType,
    CallPhase,
)
from models import (
    AvailabilityWindow,
    AvailabilityRequest,
    AvailabilityResult,
    BookRequest,
    BookResult,
    CallState,
)

REQUIRED_INTAKE_FIELDS = [
    "name",
    "phone",
    "address",
    "county",
    "property_type",
    "issue_description",
]

CALL_STATES: dict[int, CallState] = {}

_next_request_id = 1
_request_id_lock = threading.Lock()


#creates a blank CallState under a freshly generated, thread-safe incrementing id; returns that id
def get_new_requestID() -> int:
    global _next_request_id
    with _request_id_lock:
        request_id = _next_request_id
        _next_request_id += 1
        CALL_STATES[request_id] = CallState(request_id=request_id)
    return request_id


#returns the required Intake fields that are still None on this request's ServiceRequest
def get_missing_intake_fields(state: CallState) -> list[str]:
    request = state.service_request
    return [field for field in REQUIRED_INTAKE_FIELDS if getattr(request, field) is None]


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist
def update_state_intake(
    request_id: int,
    name: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    county: County | None = None,
    property_type: PropertyType | None = None,
    issue_description: str | None = None,
) -> Optional[CallState]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    request = state.service_request

    if name is not None:
        request.name = name

    if phone is not None:
        request.phone = phone

    if address is not None:
        request.address = address

    if county is not None:
        request.county = county

    if property_type is not None:
        request.property_type = property_type

    if issue_description is not None:
        request.issue_description = issue_description

    if state.phase == CallPhase.INTAKE and not get_missing_intake_fields(state):
        state.phase = CallPhase.PRIORITY_ASSESSMENT

    return state


#returns list of eligible technician ids based on county; returns all if no county specified
def _get_eligible_technicians(county: Optional[County]) -> list[int]:
    connection = sqlite3.connect("summit_air.db")
    if county:
        rows = connection.execute(
            "SELECT id FROM technicians WHERE county = ? ORDER BY id", (county,)
        ).fetchall()
    else:
        rows = connection.execute("SELECT id FROM technicians ORDER BY id").fetchall()
    connection.close()
    return [row[0] for row in rows]

#returns dict of all eligible technicians ids with list of filled appt slots ordered by start time
def _get_technician_appointments(
    technician_ids: list[int],
) -> dict[int, list[tuple[datetime, datetime]]]:
    appointments_by_technician: dict[int, list[tuple[datetime, datetime]]] = {
        technician_id: [] for technician_id in technician_ids
    }
    if not technician_ids:
        return appointments_by_technician

    connection = sqlite3.connect("summit_air.db")
    placeholders = ",".join("?" for _ in technician_ids)
    rows = connection.execute(
        f"""
        SELECT technician_id, start_time, end_time
        FROM appointments
        WHERE technician_id IN ({placeholders})
        ORDER BY technician_id, start_time
        """,
        technician_ids,
    ).fetchall()
    connection.close()

    for technician_id, start_time, end_time in rows:
        appointments_by_technician[technician_id].append(
            (datetime.fromisoformat(start_time), datetime.fromisoformat(end_time))
        )
    return appointments_by_technician


#returns True if two time slots overlap
def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


#return True if slot overlaps with any excluded slot
def _slot_is_excluded(
    slot_start: datetime, slot_end: datetime, excluded_slots: list[AvailabilityWindow]
) -> bool:
    return any(
        _overlaps(slot_start, slot_end, excluded.start, excluded.end)
        for excluded in excluded_slots
    )


#return True if slot is fully within any availability window
def _slot_within_availability(
    slot_start: datetime, slot_end: datetime, availability: list[AvailabilityWindow]
) -> bool:
    return any(
        window.start <= slot_start and slot_end <= window.end for window in availability
    )


#return True if technician is free for the slot and buffer time if required
def _technician_is_free(
    slot_start: datetime,
    slot_end: datetime,
    existing_appointments: list[tuple[datetime, datetime]],
    require_buffer: bool,
) -> bool:
    buffer = timedelta(minutes=BUFFER_MINUTES)
    for appt_start, appt_end in existing_appointments:
        if _overlaps(slot_start, slot_end, appt_start, appt_end):
            return False
        if require_buffer:
            if appt_end <= slot_start and (slot_start - appt_end) < buffer:
                return False
            if slot_end <= appt_start and (appt_start - slot_end) < buffer:
                return False
    return True


def check_availability(availability_request: AvailabilityRequest) -> AvailabilityResult:
    eligible_technicians = _get_eligible_technicians(availability_request.county)
    appointments_by_technician = _get_technician_appointments(eligible_technicians)
    require_buffer = availability_request.require_buffer

    sorted_windows = sorted(availability_request.availability, key=lambda window: window.start)
    if not sorted_windows:
        return AvailabilityResult()

    first_day = sorted_windows[0].start.date()
    last_day = max(window.end.date() for window in sorted_windows)

    day = first_day
    # go through every half hour slot from first given available time to last
    while day <= last_day:
        if day.weekday() in BUSINESS_DAYS:
            slot_start = datetime.combine(day, datetime.min.time()).replace(hour=BUSINESS_START_HOUR)
            day_end = datetime.combine(day, datetime.min.time()).replace(hour=BUSINESS_END_HOUR)

            while slot_start + timedelta(minutes=APPOINTMENT_DURATION_MINUTES) <= day_end:
                slot_end = slot_start + timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

                if not _slot_is_excluded(
                    slot_start, slot_end, availability_request.excluded_slots
                ) and _slot_within_availability(
                    slot_start, slot_end, availability_request.availability
                ):
                    #go thru technician one at a time per slot so a technician does not get over-booked
                    for technician_id in eligible_technicians:
                        existing = appointments_by_technician.get(technician_id, [])
                        if _technician_is_free(slot_start, slot_end, existing, require_buffer):
                            return AvailabilityResult(
                                available_slot=AvailabilityWindow(slot_start, slot_end),
                                technician_id=technician_id,
                            )

                slot_start += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

        day += timedelta(days=1)

    return AvailabilityResult()


#attempts to insert the appointment; success=False if (technician_id, start_time) is already booked
def book_appointment(book_request: BookRequest) -> BookResult:
    connection = sqlite3.connect("summit_air.db")
    try:
        cursor = connection.execute(
            """
            INSERT INTO appointments (
                technician_id, customer_name, customer_phone, customer_address,
                county, issue, priority, start_time, end_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                book_request.technician_id,
                book_request.customer_name,
                book_request.customer_phone,
                book_request.customer_address,
                book_request.county,
                book_request.issue,
                book_request.priority,
                book_request.start_time.isoformat(),
                book_request.end_time.isoformat(),
            ),
        )
        connection.commit()
        return BookResult(success=True, appointment_id=cursor.lastrowid)
    except sqlite3.IntegrityError:
        return BookResult(success=False)
    finally:
        connection.close()


#mocked human escalation; request_now=True for an immediate alert, False for a business-hours callback
def request_human_escalation(issue: str, request_now: bool, phone_number: str) -> bool:
    if request_now:
        print(f"Human requested now for {issue} issue. Callback at {phone_number}.")
    else:
        print(f"Human callback requested during business hours for {issue} issue. Callback at {phone_number}")
    return True
