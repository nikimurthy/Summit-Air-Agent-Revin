from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from config import (
    BookingStatus, 
    CallPhase, 
    County, 
    EscalationStatus, 
    Priority, 
    PropertyType,
    CallPhase
)

@dataclass
class AvailabilityWindow:
    start: datetime
    end: datetime


@dataclass
class AvailabilityRequest:
    availability: list[AvailabilityWindow]
    require_buffer: bool
    excluded_slots: list[AvailabilityWindow] = field(default_factory=list)
    county: Optional[County] = None


@dataclass
class AvailabilityResult:
    available_slot: Optional[AvailabilityWindow] = None
    technician_id: Optional[int] = None

@dataclass
class BookRequest:
    technician_id: int
    customer_name: str
    customer_address: str
    county: County
    issue: str
    priority: Priority
    start_time: datetime
    end_time: datetime
    customer_phone: Optional[str] = None


@dataclass
class BookResult:
    success: bool
    appointment_id: Optional[int] = None


@dataclass
class CallerInformation:
    # phase 1: intake
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    county: Optional[County] = None
    property_type: Optional[PropertyType] = None
    issue_description: Optional[str] = None

    #phase 2: priority assessment
    priority: Optional[Priority] = None

    #phase 3: request availability
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
    phase: CallPhase = CallPhase.INTAKE
    availability_attempts: int = 0
    availability_windows: list[AvailabilityWindow] = field(default_factory=list)

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


