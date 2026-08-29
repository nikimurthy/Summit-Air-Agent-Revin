from flask import Flask, request, jsonify

from config import County, PropertyType
from call_store import get_call_state, get_missing_intake_fields, update_caller_information

app = Flask(__name__)

#Vapi sends county/property_type as plain strings; only convert keys the tool call actually included
def _handle_update_caller_information(call_id: str, arguments: dict) -> dict:
    kwargs = {}

    for field in ("name", "phone", "address", "issue_description"):
        if field in arguments:
            kwargs[field] = arguments[field]

    try:
        if "county" in arguments:
            kwargs["county"] = County(arguments["county"])
        if "property_type" in arguments:
            kwargs["property_type"] = PropertyType(arguments["property_type"])
    except ValueError as error:
        return {"success": False, "error": str(error)}

    state = update_caller_information(call_id, **kwargs)
    missing_fields = get_missing_intake_fields(state)

    print(f"[{call_id}] update_caller_information arguments={arguments}", flush=True)
    print(f"[{call_id}] caller_information now: {state.to_dict()['caller_information']}", flush=True)
    print(f"[{call_id}] phase={state.phase.value} missing_fields={missing_fields}", flush=True)

    return {
        "success": True,
        "current_phase": state.phase.value,
        "phase_complete": not missing_fields,
        "missing_fields": missing_fields,
    }


@app.route("/vapi/tool-calls", methods=["POST"])
def vapi_tool_calls():
    payload = request.get_json(force=True)
    message = payload["message"]
    call_id = message["call"]["id"]

    results = []
    for tool_call in message["toolCalls"]:
        tool_call_id = tool_call["id"]
        function_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]

        if function_name == "update_caller_information":
            result = _handle_update_caller_information(call_id, arguments)
        else:
            result = {"success": False, "error": f"unsupported tool: {function_name}"}

        results.append({"toolCallId": tool_call_id, "result": result})

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(port=5001, debug=True)  # 5000 conflicts with macOS Control Center (AirPlay Receiver)
