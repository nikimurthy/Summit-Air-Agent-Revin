from datetime import datetime

from flask import Flask, request, jsonify

from config import County, Priority, PropertyType
from models import AvailabilityWindow
from tools import (
    CALL_STATES,
    book_appointment_for_request,
    check_availability_for_request,
    find_technician,
    get_current_timestamp,
    get_missing_intake_fields,
    get_new_requestID,
    get_state,
    request_human_escalation,
    save_service_request,
    update_availability_windows,
    update_raw_availability,
    update_state_intake,
    update_state_priority,
)

app = Flask(__name__)


def _intake_result(
    success: bool,
    current_phase: str | None,
    phase_complete: bool,
    missing_fields: list[str],
    error_type: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "success": success,
        "current_phase": current_phase,
        "phase_complete": phase_complete,
        "missing_fields": missing_fields,
        "error_type": error_type,
        "message": message,
    }


def _handle_get_new_requestID() -> dict:
    request_id = get_new_requestID()
    print(f"[new request] created requestID={request_id}", flush=True)
    return {"success": True, "requestID": request_id, "error_type": None, "message": None}


#Vapi sends county/property_type as plain strings; only convert keys the tool call actually included
def _handle_update_state_intake(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return _intake_result(False, None, False, [], "missing_request_id", "requestID is required.")

    state = CALL_STATES.get(request_id)
    if state is None:
        return _intake_result(
            False, None, False, [], "not_found", f"No service request found for requestID {request_id}."
        )

    current_phase = state.phase.value
    missing_fields_before = get_missing_intake_fields(state)

    kwargs = {}
    for field in ("name", "phone", "address", "issue_description"):
        if field in arguments:
            kwargs[field] = arguments[field]

    if "county" in arguments:
        try:
            kwargs["county"] = County(arguments["county"])
        except ValueError:
            return _intake_result(
                False, current_phase, not missing_fields_before, missing_fields_before,
                "invalid_value", "County must be County Alpha, County Bravo, or County Charlie.",
            )

    if "property_type" in arguments:
        try:
            kwargs["property_type"] = PropertyType(arguments["property_type"])
        except ValueError:
            return _intake_result(
                False, current_phase, not missing_fields_before, missing_fields_before,
                "invalid_value", "property_type must be residential or commercial.",
            )

    state = update_state_intake(request_id, **kwargs)
    missing_fields = get_missing_intake_fields(state)

    print(f"[{request_id}] update_state_intake arguments={arguments}", flush=True)
    print(f"[{request_id}] service_request now: {state.to_dict()['service_request']}", flush=True)
    print(f"[{request_id}] phase={state.phase.value} missing_fields={missing_fields}", flush=True)

    return _intake_result(True, state.phase.value, not missing_fields, missing_fields)


def _priority_result(
    success: bool,
    current_phase: str | None,
    error_type: str | None = None,
    message: str | None = None,
) -> dict:
    return {
        "success": success,
        "current_phase": current_phase,
        "error_type": error_type,
        "message": message,
    }


def _handle_update_state_priority(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return _priority_result(False, None, "missing_request_id", "requestID is required.")

    state = CALL_STATES.get(request_id)
    if state is None:
        return _priority_result(
            False, None, "not_found", f"No service request found for requestID {request_id}."
        )

    priority_raw = arguments.get("priority")
    if priority_raw is None:
        return _priority_result(False, state.phase.value, "missing_field", "priority is required.")

    try:
        priority = Priority(priority_raw)
    except ValueError:
        return _priority_result(
            False, state.phase.value, "invalid_value", "priority must be routine, urgent, or emergency."
        )

    state = update_state_priority(request_id, priority, issue_description=arguments.get("issue_description"))

    print(f"[{request_id}] update_state_priority arguments={arguments}", flush=True)
    print(f"[{request_id}] priority now: {state.service_request.priority.value}", flush=True)
    print(f"[{request_id}] phase={state.phase.value}", flush=True)

    return _priority_result(True, state.phase.value)


def _handle_update_raw_availability(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "error_type": "missing_request_id", "message": "requestID is required."}

    raw_text = arguments.get("raw_text")
    if not raw_text:
        return {"success": False, "error_type": "missing_field", "message": "raw_text is required."}

    state = update_raw_availability(request_id, raw_text)
    if state is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    print(f"[{request_id}] availability_raw now: {state.service_request.availability_raw}", flush=True)

    return {"success": True, "error_type": None, "message": None}


def _handle_update_availability_windows(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "error_type": "missing_request_id", "message": "requestID is required."}

    if CALL_STATES.get(request_id) is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    windows_raw = arguments.get("availability_windows")
    if not windows_raw:
        return {
            "success": False,
            "error_type": "missing_field",
            "message": "availability_windows is required and must be non-empty.",
        }

    try:
        windows = [
            AvailabilityWindow(start=datetime.fromisoformat(w["start"]), end=datetime.fromisoformat(w["end"]))
            for w in windows_raw
        ]
    except (KeyError, ValueError):
        return {
            "success": False,
            "error_type": "invalid_value",
            "message": "Each availability window needs valid ISO 'start' and 'end' datetimes.",
        }

    state = update_availability_windows(request_id, windows)

    print(f"[{request_id}] availability_windows now: {state.service_request.availability_windows}", flush=True)

    return {"success": True, "error_type": None, "message": None}


def _handle_check_availability(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "found": False, "error_type": "missing_request_id", "message": "requestID is required."}

    result = check_availability_for_request(request_id)
    if result is None:
        return {
            "success": False,
            "found": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    if result.available_slot is None:
        return {"success": True, "found": False, "error_type": None, "message": None}

    print(
        f"[{request_id}] check_availability -> technician_id={result.technician_id} "
        f"slot={result.available_slot.start} - {result.available_slot.end}",
        flush=True,
    )

    return {
        "success": True,
        "found": True,
        "technician_id": result.technician_id,
        "start": result.available_slot.start.isoformat(),
        "end": result.available_slot.end.isoformat(),
        "error_type": None,
        "message": None,
    }


def _handle_book_appointment(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "current_phase": None, "error_type": "missing_request_id", "message": "requestID is required."}

    technician_id = arguments.get("technician_id")
    start = arguments.get("start")
    end = arguments.get("end")
    if technician_id is None or start is None or end is None:
        return {
            "success": False,
            "current_phase": None,
            "error_type": "missing_field",
            "message": "technician_id, start, and end are all required.",
        }

    try:
        start_time = datetime.fromisoformat(start)
        end_time = datetime.fromisoformat(end)
    except ValueError:
        return {
            "success": False,
            "current_phase": None,
            "error_type": "invalid_value",
            "message": "start and end must be valid ISO datetimes.",
        }

    result = book_appointment_for_request(request_id, technician_id, start_time, end_time)
    if result is None:
        return {
            "success": False,
            "current_phase": None,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    state = CALL_STATES[request_id]

    if not result.success:
        return {
            "success": False,
            "current_phase": state.phase.value,
            "error_type": "slot_unavailable",
            "message": "That slot is no longer available.",
        }

    print(f"[{request_id}] booked appointment_id={result.appointment_id}, phase={state.phase.value}", flush=True)

    return {
        "success": True,
        "appointment_id": result.appointment_id,
        "current_phase": state.phase.value,
        "error_type": None,
        "message": None,
    }


def _handle_find_technician(arguments: dict) -> dict:
    technician_id = arguments.get("technician_id")
    if technician_id is None:
        return {"success": False, "error_type": "missing_field", "message": "technician_id is required."}

    technician = find_technician(technician_id)
    if technician is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No technician found for id {technician_id}.",
        }

    return {
        "success": True,
        "name": technician.name,
        "county": technician.county.value,
        "error_type": None,
        "message": None,
    }


def _handle_get_current_timestamp() -> dict:
    now = get_current_timestamp()
    return {
        "success": True,
        "current_datetime": now.isoformat(),
        "current_weekday": now.strftime("%A"),
        "error_type": None,
        "message": None,
    }


def _handle_save_service_request(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "error_type": "missing_request_id", "message": "requestID is required."}

    state = CALL_STATES.get(request_id)
    if state is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    save_service_request(state)
    print(f"[{request_id}] service request saved to database", flush=True)

    return {"success": True, "error_type": None, "message": None}


#returns every service_request/service_outcome field, substituting a default for anything unset
def _handle_get_state(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "error_type": "missing_request_id", "message": "requestID is required."}

    state = get_state(request_id)
    if state is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    request = state.service_request
    outcome = state.service_outcome

    return {
        "success": True,
        "requestID": state.request_id,
        "phase": state.phase.value,
        "name": request.name or "",
        "phone": request.phone or "",
        "address": request.address or "",
        "county": request.county.value if request.county else "",
        "property_type": request.property_type.value if request.property_type else "",
        "issue_description": request.issue_description or "",
        "priority": request.priority.value if request.priority else "",
        "availability_raw": request.availability_raw or "",
        "appointment_id": outcome.appointment_id,
        "booking_status": outcome.booking_status.value,
        "escalation_status": outcome.escalation_status.value,
        "error_type": None,
        "message": None,
    }


def _handle_request_human_escalation(arguments: dict) -> dict:
    request_id = arguments.get("requestID")
    if request_id is None:
        return {"success": False, "error_type": "missing_request_id", "message": "requestID is required."}

    issue = arguments.get("issue")
    request_now = arguments.get("request_now")
    phone_number = arguments.get("phone_number")

    if issue is None or request_now is None or phone_number is None:
        return {
            "success": False,
            "error_type": "missing_field",
            "message": "issue, request_now, and phone_number are all required.",
        }

    state = request_human_escalation(request_id, issue, request_now, phone_number)
    if state is None:
        return {
            "success": False,
            "error_type": "not_found",
            "message": f"No service request found for requestID {request_id}.",
        }

    print(f"[{request_id}] escalation_status now: {state.service_outcome.escalation_status.value}", flush=True)

    return {"success": True, "error_type": None, "message": None}


_HANDLERS = {
    "update_state_intake": lambda args: _handle_update_state_intake(args),
    "get_new_requestID": lambda args: _handle_get_new_requestID(),
    "request_human_escalation": lambda args: _handle_request_human_escalation(args),
    "update_state_priority": lambda args: _handle_update_state_priority(args),
    "get_state": lambda args: _handle_get_state(args),
    "update_raw_availability": lambda args: _handle_update_raw_availability(args),
    "update_availability_windows": lambda args: _handle_update_availability_windows(args),
    "check_availability": lambda args: _handle_check_availability(args),
    "book_appointment": lambda args: _handle_book_appointment(args),
    "find_technician": lambda args: _handle_find_technician(args),
    "get_current_timestamp": lambda args: _handle_get_current_timestamp(),
    "save_service_request": lambda args: _handle_save_service_request(args),
}


@app.route("/vapi/tool-calls", methods=["POST"])
def vapi_tool_calls():
    payload = request.get_json(force=True)
    message = payload["message"]

    results = []
    for tool_call in message["toolCalls"]:
        tool_call_id = tool_call["id"]
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]

        handler = _HANDLERS.get(function_name)
        if handler is None:
            result = {"success": False, "error_type": "unsupported_tool", "message": f"unsupported tool: {function_name}"}
        else:
            result = handler(arguments)

        results.append({"toolCallId": tool_call_id, "result": result})

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(port=5001, debug=True)  # 5000 conflicts with macOS Control Center (AirPlay Receiver)
