from models import (
    AvailabilityWindow,
    AvailabilityRequest,
    AvailabilityResult,
    BookRequest,
    BookResult,
    County,
    PropertyType,
    CallPhase,
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

CALL_STATES: dict[str, CallState] = {}

def get_call_state(call_id: str) -> CallState:
    if call_id not in CALL_STATES:
        CALL_STATES[call_id] = CallState()

    return CALL_STATES[call_id]


#returns the required Intake fields that are still None on this call's CallerInformation
def get_missing_intake_fields(state: CallState) -> list[str]:
    info = state.caller_information
    return [field for field in REQUIRED_INTAKE_FIELDS if getattr(info, field) is None]


def update_caller_information(
    call_id: str,
    name: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    county: County | None = None,
    property_type: PropertyType | None = None,
    issue_description: str | None = None,
) -> CallState:
    state = get_call_state(call_id)
    info = state.caller_information

    if name is not None:
        info.name = name

    if phone is not None:
        info.phone = phone

    if address is not None:
        info.address = address

    if county is not None:
        info.county = county

    if property_type is not None:
        info.property_type = property_type

    if issue_description is not None:
        info.issue_description = issue_description

    if state.phase == CallPhase.INTAKE and not get_missing_intake_fields(state):
        state.phase = CallPhase.PRIORITY_ASSESSMENT

    return state