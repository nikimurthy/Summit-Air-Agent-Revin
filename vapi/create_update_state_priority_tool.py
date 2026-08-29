"""One-time creation of the 'update_state_priority' custom function tool.

Run this once:
    python3 vapi/create_update_state_priority_tool.py

Saves the returned tool id to vapi/tools/update_state_priority_tool_id.txt,
which publish_prompts.py then reads and includes in toolIds. Safe to re-run
only if you first delete the tool on Vapi's side and the saved id file —
running it again without doing that would create a duplicate tool.
"""
import json
import os
import urllib.request

TOOL_DEFINITION_PATH = "vapi/tools/update_state_priority.json"
TOOL_ID_PATH = "vapi/tools/update_state_priority_tool_id.txt"


def _read_api_key() -> str:
    with open(os.path.expanduser("~/.vapi-cli.yaml")) as f:
        for line in f:
            if line.startswith("api_key:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("api_key not found in ~/.vapi-cli.yaml")


def main() -> None:
    if os.path.exists(TOOL_ID_PATH):
        raise SystemExit(
            f"{TOOL_ID_PATH} already exists (id: {open(TOOL_ID_PATH).read().strip()}). "
            "Delete it (and the tool on Vapi's side, if it exists) before re-running, "
            "to avoid creating a duplicate update_state_priority tool."
        )

    body = json.load(open(TOOL_DEFINITION_PATH))
    request = urllib.request.Request(
        "https://api.vapi.ai/tool",
        method="POST",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {_read_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "summit-air-agent/1.0",
        },
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    with open(TOOL_ID_PATH, "w") as f:
        f.write(result["id"])

    print(f"Created update_state_priority tool: {result['id']}")
    print(f"Saved to {TOOL_ID_PATH}. publish_prompts.py will pick it up automatically.")


if __name__ == "__main__":
    main()
