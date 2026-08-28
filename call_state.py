from dataclasses import dataclass, field
from typing import Optional

from config import BookingStatus, County, EscalationStatus, Priority, PropertyType


@dataclass
class CallerInformation:
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    county: Optional[County] = None
    property_type: Optional[PropertyType] = None
    issue_description: Optional[str] = None
    priority: Optional[Priority] = None
    availability_raw: Optional[str] = None


@dataclass
class CallerOutcome:
    appointment_id: Optional[int] = None
    booking_status: BookingStatus = BookingStatus.NOT_BOOKED
    escalation_status: EscalationStatus = EscalationStatus.NOT_REQUIRED


@dataclass
class CallState:
    caller_information: CallerInformation = field(default_factory=CallerInformation)
    caller_outcome: CallerOutcome = field(default_factory=CallerOutcome)

    def to_dict(self) -> dict:
        info = self.caller_information
        outcome = self.caller_outcome
        return {
            "caller_information": {
                "name": info.name,
                "phone": info.phone,
                "address": info.address,
                "county": info.county.value if info.county else None,
                "property_type": info.property_type.value if info.property_type else None,
                "issue_description": info.issue_description,
                "priority": info.priority.value if info.priority else None,
                "availability_raw": info.availability_raw,
            },
            "caller_outcome": {
                "appointment_id": outcome.appointment_id,
                "booking_status": outcome.booking_status.value,
                "escalation_status": outcome.escalation_status.value,
            },
        }
