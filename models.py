from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from config import (
    BookingStatus,
    CallPhase,
    County,
    EscalationStatus,
    Priority,
    PropertyType,
)

@dataclass
class AvailabilityWindow:
    start: datetime
    end: datetime


@dataclass
class AvailabilityRequest:
    availability: list[AvailabilityWindow]
    require_buffer: bool
    required_county: Optional[County] = None  # hard filter: only these technicians are eligible at all
    preferred_county: Optional[County] = None  # soft tiebreak: prefer this county among ties at the same slot


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
    request_id: Optional[int] = None


@dataclass
class BookResult:
    success: bool
    appointment_id: Optional[int] = None


@dataclass
class Appointment:
    id: int
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
class Technician:
    id: int
    name: str
    county: County


@dataclass
class ServiceRequest:
    # phase 1: intake
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    county: Optional[County] = None
    property_type: Optional[PropertyType] = None
    issue_description: Optional[str] = None

    # phase 2: priority assessment
    priority: Optional[Priority] = None

    # phase 3: scheduling
    availability_raw: Optional[str] = None
    availability_windows: list[AvailabilityWindow] = field(default_factory=list)



@dataclass
class ServiceOutcome:
    appointment_id: Optional[int] = None
    booking_status: BookingStatus = BookingStatus.NOT_BOOKED
    escalation_status: EscalationStatus = EscalationStatus.NOT_REQUIRED


@dataclass
class CallState:
    request_id: Optional[int] = None
    service_request: ServiceRequest = field(default_factory=ServiceRequest)
    service_outcome: ServiceOutcome = field(default_factory=ServiceOutcome)
    phase: CallPhase = CallPhase.INTAKE

    def to_dict(self) -> dict:
        request = self.service_request
        outcome = self.service_outcome
        return {
            "request_id": self.request_id,
            "service_request": {
                "name": request.name,
                "phone": request.phone,
                "address": request.address,
                "county": request.county.value if request.county else None,
                "property_type": request.property_type.value if request.property_type else None,
                "issue_description": request.issue_description,
                "priority": request.priority.value if request.priority else None,
                "availability_raw": request.availability_raw,
            },
            "service_outcome": {
                "appointment_id": outcome.appointment_id,
                "booking_status": outcome.booking_status.value,
                "escalation_status": outcome.escalation_status.value,
            },
        }
