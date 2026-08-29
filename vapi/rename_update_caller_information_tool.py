"""One-time rename of the existing 'update_caller_information' tool to 'update_state_intake'.

Run this once, after reviewing vapi/tools/update_state_intake.json:
    python3 vapi/rename_update_caller_information_tool.py

PATCHes the existing tool object in place (same id, same underlying tool —
just new name/description/parameters/server.url) so publish_phase1_prompt.py's
toolIds reference keeps working without any change.
"""
import json
import os
import urllib.request

EXISTING_TOOL_ID = "056fe118-b451-4b1b-8c68-ddb721e3344d"  # the tool previously named update_caller_information
TOOL_DEFINITION_PATH = "vapi/tools/update_state_intake.json"


def _read_api_key() -> str:
    with open(os.path.expanduser("~/.vapi-cli.yaml")) as f:
        for line in f:
            if line.startswith("api_key:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("api_key not found in ~/.vapi-cli.yaml")


def main() -> None:
    body = json.load(open(TOOL_DEFINITION_PATH))
    # PATCH /tool/{id} only accepts function/server fields, not "type" (immutable on an existing tool)
    body.pop("type", None)

    request = urllib.request.Request(
        f"https://api.vapi.ai/tool/{EXISTING_TOOL_ID}",
        method="PATCH",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {_read_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "summit-air-agent/1.0",
        },
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    print(f"Renamed tool {EXISTING_TOOL_ID} -> function.name={result['function']['name']}")


if __name__ == "__main__":
    main()
