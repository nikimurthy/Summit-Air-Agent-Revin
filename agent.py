from flask import Flask, request, jsonify

from config import County, Priority, PropertyType
from tools import (
    CALL_STATES,
    get_missing_intake_fields,
    get_new_requestID,
    request_human_escalation,
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


def _handle_request_human_escalation(arguments: dict) -> dict:
    issue = arguments.get("issue")
    request_now = arguments.get("request_now")
    phone_number = arguments.get("phone_number")

    if issue is None or request_now is None or phone_number is None:
        return {
            "success": False,
            "error_type": "missing_field",
            "message": "issue, request_now, and phone_number are all required.",
        }

    success = request_human_escalation(issue, request_now, phone_number)
    return {"success": success, "error_type": None, "message": None}


@app.route("/vapi/tool-calls", methods=["POST"])
def vapi_tool_calls():
    payload = request.get_json(force=True)
    message = payload["message"]

    results = []
    for tool_call in message["toolCalls"]:
        tool_call_id = tool_call["id"]
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]

        if function_name == "update_state_intake":
            result = _handle_update_state_intake(arguments)
        elif function_name == "get_new_requestID":
            result = _handle_get_new_requestID()
        elif function_name == "request_human_escalation":
            result = _handle_request_human_escalation(arguments)
        elif function_name == "update_state_priority":
            result = _handle_update_state_priority(arguments)
        else:
            result = {"success": False, "error_type": "unsupported_tool", "message": f"unsupported tool: {function_name}"}

        results.append({"toolCallId": tool_call_id, "result": result})

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(port=5001, debug=True)  # 5000 conflicts with macOS Control Center (AirPlay Receiver)
