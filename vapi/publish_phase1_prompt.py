"""Pushes the current contents of phase1_intake_system_prompt.md live to the Vapi assistant.

Run this every time the prompt file is edited:
    python3 vapi/publish_phase1_prompt.py

Rewrites vapi/assistant_patch.json (the diff just sent) and
vapi/current_assistant_snapshot.json (the resulting live state) so the repo
stays in sync with whatever's actually live on Vapi.
"""
import json
import os
import urllib.request

ASSISTANT_ID = "75bb9109-bb9a-460d-8fcd-3545a6484358"
UPDATE_STATE_INTAKE_TOOL_ID = "056fe118-b451-4b1b-8c68-ddb721e3344d"  # renamed via rename_update_caller_information_tool.py

PROMPT_PATH = "vapi/prompts/phase1_intake_prompt.md"
FIRST_MESSAGE_PATH = "vapi/prompts/phase1_first_message.txt"
END_CALL_TOOL_ID_PATH = "vapi/tools/end_call_tool_id.txt"  # written by create_end_call_tool.py
GET_NEW_REQUEST_ID_TOOL_ID_PATH = "vapi/tools/get_new_requestID_tool_id.txt"  # written by create_get_new_requestID_tool.py
HUMAN_ESCALATION_TOOL_ID_PATH = "vapi/tools/request_human_escalation_tool_id.txt"  # written by create_request_human_escalation_tool.py
PATCH_PATH = "vapi/assistant_patch.json"
SNAPSHOT_PATH = "vapi/current_assistant_snapshot.json"


def _read_api_key() -> str:
    with open(os.path.expanduser("~/.vapi-cli.yaml")) as f:
        for line in f:
            if line.startswith("api_key:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("api_key not found in ~/.vapi-cli.yaml")


def main() -> None:
    prompt = open(PROMPT_PATH).read().strip()
    first_message = open(FIRST_MESSAGE_PATH).read().strip()

    tool_ids = [UPDATE_STATE_INTAKE_TOOL_ID]
    if os.path.exists(END_CALL_TOOL_ID_PATH):
        tool_ids.append(open(END_CALL_TOOL_ID_PATH).read().strip())
    else:
        print(f"NOTE: {END_CALL_TOOL_ID_PATH} not found — publishing without the endCall tool. "
              "Run vapi/create_end_call_tool.py first if you want it included.")

    if os.path.exists(GET_NEW_REQUEST_ID_TOOL_ID_PATH):
        tool_ids.append(open(GET_NEW_REQUEST_ID_TOOL_ID_PATH).read().strip())
    else:
        print(f"NOTE: {GET_NEW_REQUEST_ID_TOOL_ID_PATH} not found — publishing without get_new_requestID. "
              "Run vapi/create_get_new_requestID_tool.py first if you want it included.")

    if os.path.exists(HUMAN_ESCALATION_TOOL_ID_PATH):
        tool_ids.append(open(HUMAN_ESCALATION_TOOL_ID_PATH).read().strip())
    else:
        print(f"NOTE: {HUMAN_ESCALATION_TOOL_ID_PATH} not found — publishing without request_human_escalation. "
              "Run vapi/create_request_human_escalation_tool.py first if you want it included.")

    patch = {
        "firstMessage": first_message,
        "model": {
            "provider": "openai",
            "model": "gpt-4.1",
            "messages": [{"role": "system", "content": prompt}],
            "toolIds": tool_ids,
        }
    }
    with open(PATCH_PATH, "w") as f:
        json.dump(patch, f, indent=2)

    request = urllib.request.Request(
        f"https://api.vapi.ai/assistant/{ASSISTANT_ID}",
        method="PATCH",
        data=json.dumps(patch).encode(),
        headers={
            "Authorization": f"Bearer {_read_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "summit-air-agent/1.0",  # urllib's default UA gets blocked by Vapi's Cloudflare WAF
        },
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Published. latestVersion={result.get('latestVersion')}. Live — ready to test.")

if __name__ == "__main__":
    main()
