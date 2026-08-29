from enum import Enum

BUSINESS_START_HOUR = 8
BUSINESS_END_HOUR = 17

APPOINTMENT_DURATION_MINUTES = 30
BUFFER_MINUTES = 30

BUSINESS_DAYS = {
    0, 1, 2, 3, 4
}

ROUTINE_BOOKING_WINDOW_DAYS = 14
URGENT_BOOKING_WINDOW_DAYS = 7
EMERGENCY_BOOKING_WINDOW_DAYS = 7

MAX_SCHEDULING_ATTEMPTS = 3

class County(str, Enum):
    ALPHA = "County Alpha"
    BRAVO = "County Bravo"
    CHARLIE = "County Charlie"

COUNTIES = list(County)

class PropertyType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


class Priority(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"

class BookingStatus(str, Enum):
    NOT_BOOKED = "not_booked"
    BOOKED = "booked"
    UNABLE_TO_BOOK = "unable_to_book"

class EscalationStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    IMMEDIATE_REQUEST = "immediate_request"
    CALLBACK_REQUEST = "callback_request"

class CallPhase(str, Enum):
    INTAKE = "intake"
    PRIORITY_ASSESSMENT = "priority_assessment"
    CALLER_AVAILABILITY = "request_availability"
    FIND_SLOT = "find_slot"
    BOOK_APPOINTMENT = "booking_appointment"
    SUMMARIZE = "summarize"




