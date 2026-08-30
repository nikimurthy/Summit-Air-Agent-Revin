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
    BookingStatus,
    County,
    EscalationStatus,
    Priority,
    PropertyType,
    CallPhase,
)
from models import (
    Appointment,
    AvailabilityWindow,
    AvailabilityRequest,
    AvailabilityResult,
    BookRequest,
    BookResult,
    CallState,
    Technician,
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


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist
def get_state(request_id: int) -> Optional[CallState]:
    return CALL_STATES.get(request_id)


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


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist
def update_state_priority(
    request_id: int,
    priority: Priority,
    issue_description: str | None = None,
) -> Optional[CallState]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    request = state.service_request
    request.priority = priority

    if issue_description is not None:
        request.issue_description = issue_description

    if state.phase == CallPhase.PRIORITY_ASSESSMENT:
        state.phase = CallPhase.CALLER_AVAILABILITY

    return state


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist.
#raw_text is APPENDED to the running log of what the caller has said about availability,
#rather than replaced, so the caller never has to repeat earlier statements to add more.
def update_raw_availability(request_id: int, raw_text: str) -> Optional[CallState]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    request = state.service_request
    if request.availability_raw:
        request.availability_raw = f"{request.availability_raw} | {raw_text}"
    else:
        request.availability_raw = raw_text

    return state


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist.
#REPLACES the entire prior set of windows — the caller's full current availability,
#recomputed by the LLM each time (e.g. after rejecting an offered slot), not a partial patch.
def update_availability_windows(
    request_id: int, availability_windows: list[AvailabilityWindow]
) -> Optional[CallState]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    state.service_request.availability_windows = availability_windows
    return state


#returns the current server date/time, so the LLM has a real anchor for relative dates
def get_current_timestamp() -> datetime:
    return datetime.now()


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


#returns {technician_id: county} for the given technicians
def _get_technician_counties(technician_ids: list[int]) -> dict[int, County]:
    if not technician_ids:
        return {}
    connection = sqlite3.connect("summit_air.db")
    placeholders = ",".join("?" for _ in technician_ids)
    rows = connection.execute(
        f"SELECT id, county FROM technicians WHERE id IN ({placeholders})", technician_ids
    ).fetchall()
    connection.close()
    return {tech_id: County(county) for tech_id, county in rows}

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

    #tiebreak only — never restricts eligibility, only changes which of several technicians
    #tied for the same earliest slot gets checked (and therefore picked) first
    preferred_county = availability_request.preferred_county
    if preferred_county is not None:
        technician_counties = _get_technician_counties(eligible_technicians)
        eligible_technicians = sorted(
            eligible_technicians,
            key=lambda tech_id: technician_counties.get(tech_id) != preferred_county,
        )

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

                if _slot_within_availability(
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


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist.
#assembles the AvailabilityRequest from stored state per priority's business rule, so the
#caller (Vapi) only ever needs to pass requestID:
#  ROUTINE -> restricted to the caller's own county, buffer required
#  URGENT/EMERGENCY -> any technician, no buffer (county still preferred as a same-slot tiebreak)
def check_availability_for_request(request_id: int) -> Optional[AvailabilityResult]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    request = state.service_request
    is_routine = request.priority == Priority.ROUTINE

    availability_request = AvailabilityRequest(
        availability=request.availability_windows,
        require_buffer=is_routine,
        county=request.county if is_routine else None,
        preferred_county=request.county,
    )
    return check_availability(availability_request)


#returns the Technician for technician_id, or None if no such technician exists
def find_technician(technician_id: int) -> Optional[Technician]:
    connection = sqlite3.connect("summit_air.db")
    row = connection.execute(
        "SELECT id, name, county FROM technicians WHERE id = ?", (technician_id,)
    ).fetchone()
    connection.close()
    if row is None:
        return None
    tech_id, name, county = row
    return Technician(id=tech_id, name=name, county=County(county))


#returns the full Appointment for appointment_id, or None if no such appointment exists
def find_appointment(appointment_id: int) -> Optional[Appointment]:
    connection = sqlite3.connect("summit_air.db")
    row = connection.execute(
        """
        SELECT id, technician_id, customer_name, customer_phone, customer_address,
               county, issue, priority, start_time, end_time
        FROM appointments
        WHERE id = ?
        """,
        (appointment_id,),
    ).fetchone()
    connection.close()
    if row is None:
        return None

    (appt_id, technician_id, customer_name, customer_phone, customer_address,
     county, issue, priority, start_time, end_time) = row

    return Appointment(
        id=appt_id,
        technician_id=technician_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        county=County(county),
        issue=issue,
        priority=Priority(priority),
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
    )


#attempts to insert the appointment; success=False if (technician_id, start_time) is already booked
def book_appointment(book_request: BookRequest) -> BookResult:
    connection = sqlite3.connect("summit_air.db")
    try:
        cursor = connection.execute(
            """
            INSERT INTO appointments (
                technician_id, customer_name, customer_phone, customer_address,
                county, issue, priority, start_time, end_time, service_request_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                book_request.request_id,
            ),
        )
        connection.commit()
        return BookResult(success=True, appointment_id=cursor.lastrowid)
    except sqlite3.IntegrityError:
        return BookResult(success=False)
    finally:
        connection.close()


#looks up an existing request by id; returns None (no implicit creation) if it doesn't exist.
#builds the BookRequest entirely from stored state plus the one slot being booked (technician_id
#+ start/end, as returned by check_availability_for_request). On success, marks the request
#booked and advances to SUMMARIZE. On failure (slot taken since it was offered), state is left
#unchanged — the caller must recheck availability and offer a new slot, not retry blindly.
def book_appointment_for_request(
    request_id: int, technician_id: int, start_time: datetime, end_time: datetime
) -> Optional[BookResult]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    request = state.service_request
    book_request = BookRequest(
        technician_id=technician_id,
        customer_name=request.name,
        customer_address=request.address,
        county=request.county,
        issue=request.issue_description,
        priority=request.priority,
        start_time=start_time,
        end_time=end_time,
        customer_phone=request.phone,
        request_id=request_id,
    )
    result = book_appointment(book_request)

    if result.success:
        state.service_outcome.appointment_id = result.appointment_id
        state.service_outcome.booking_status = BookingStatus.BOOKED
        state.phase = CallPhase.SUMMARIZE

    return result


#mocked human escalation; request_now=True for an immediate alert, False for a business-hours callback
def request_human_escalation(
    request_id: int, issue: str, request_now: bool, phone_number: str
) -> Optional[CallState]:
    state = CALL_STATES.get(request_id)
    if state is None:
        return None

    state.service_outcome.escalation_status = (
        EscalationStatus.IMMEDIATE_REQUEST if request_now else EscalationStatus.CALLBACK_REQUEST
    )

    if request_now:
        print(f"Human requested now for {issue} issue. Callback at {phone_number}.")
    else:
        print(f"Human callback requested during business hours for {issue} issue. Callback at {phone_number}")

    return state


#persists the given request's current state to the service_requests table, keyed by request_id.
#does NOT persist availability_windows (no clean scalar representation; availability_raw and the
#eventual outcome — a booked appointment or an escalation — already capture what matters).
#not yet wired to any automatic trigger; caller decides when a request is actually "done".
def save_service_request(state: CallState) -> None:
    request = state.service_request
    outcome = state.service_outcome

    connection = sqlite3.connect("summit_air.db")
    connection.execute(
        """
        INSERT OR REPLACE INTO service_requests (
            request_id, name, phone, address, county, property_type, issue_description,
            priority, availability_raw, appointment_id, booking_status, escalation_status, final_phase
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            state.request_id,
            request.name,
            request.phone,
            request.address,
            request.county,
            request.property_type,
            request.issue_description,
            request.priority,
            request.availability_raw,
            outcome.appointment_id,
            outcome.booking_status.value,
            outcome.escalation_status.value,
            state.phase.value,
        ),
    )
    connection.commit()
    connection.close()
