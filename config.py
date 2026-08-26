from enum import Enum

BUSINESS_START_HOUR = 8
BUSINESS_END_HOUR = 17

APPOINTMENT_DURATION_MINUTES = 30
BUFFER_MINUTES = 30

BUSINESS_DAYS = {
    0, 1, 2, 3, 4
}

LOCAL_BOOKING_WINDOW_DAYS = 14

COUNTIES = [
    "County Alpha",
    "County Bravo",
    "County Charlie",
]

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
    REQUESTED = "requested"





