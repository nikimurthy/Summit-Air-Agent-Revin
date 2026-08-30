"""Pushes the combined global-behavior + phase 1-4 prompts + first message live to the Vapi assistant.

Run this every time any phase prompt file is edited:
    python3 vapi/publish_prompts.py

Vapi only accepts a single system prompt string, so this concatenates all
phase prompt files, in phase order, into one combined prompt. Each phase
file stays the authored, reviewable source of truth — this script is just
the thing that glues them together right before sending. Empty phase files
(phases not written yet) are skipped rather than contributing a blank
section. Rewrites vapi/assistant_patch.json (the diff just sent) and
vapi/current_assistant_snapshot.json (the resulting live state) so the repo
stays in sync with whatever's actually live on Vapi.
"""
import json
import os
import urllib.request

ASSISTANT_ID = "75bb9109-bb9a-460d-8fcd-3545a6484358"

UPDATE_STATE_INTAKE_TOOL_ID = "056fe118-b451-4b1b-8c68-ddb721e3344d"  # renamed via rename_update_caller_information_tool.py

PHASE_PROMPT_PATHS = [
    "vapi/prompts/global_behavior_prompt.md",
    "vapi/prompts/phase1_intake_prompt.md",
    "vapi/prompts/phase2_priority_assessment_prompt.md",
    "vapi/prompts/phase3_scheduling_prompt.md",
    "vapi/prompts/phase4_summarize_prompt.md",
]
FIRST_MESSAGE_PATH = "vapi/prompts/first_message.txt"

TOOL_IDS_PATH = "vapi/tools/tool_ids.txt"  # lines of "<label> id: <uuid>"

PATCH_PATH = "vapi/assistant_patch.json"
SNAPSHOT_PATH = "vapi/current_assistant_snapshot.json"


def _read_api_key() -> str:
    with open(os.path.expanduser("~/.vapi-cli.yaml")) as f:
        for line in f:
            if line.startswith("api_key:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("api_key not found in ~/.vapi-cli.yaml")


def _build_combined_prompt() -> str:
    sections = []
    for path in PHASE_PROMPT_PATHS:
        content = open(path).read().strip()
        if content:
            sections.append(content)
        else:
            print(f"NOTE: {path} is empty — skipping (no section added for this phase yet).")
    return "\n\n---\n\n".join(sections)


def _load_tool_ids() -> dict[str, str]:
    tool_ids = {}
    if not os.path.exists(TOOL_IDS_PATH):
        return tool_ids
    for line in open(TOOL_IDS_PATH):
        label, sep, tool_id = line.strip().partition(" id: ")
        if sep:
            tool_ids[label.strip()] = tool_id.strip()
    return tool_ids


def _optional_tool_id(loaded_tool_ids: dict[str, str], label: str) -> list[str]:
    if label in loaded_tool_ids:
        return [loaded_tool_ids[label]]
    print(f"NOTE: no '{label}' entry in {TOOL_IDS_PATH} — publishing without it. "
          f"Create that tool and add its id there if you want it included.")
    return []


def main() -> None:
    prompt = _build_combined_prompt()
    first_message = open(FIRST_MESSAGE_PATH).read().strip()

    optional_tool_labels = [
        "end_call",
        "get_new_requestID",
        "request_human_escalation",
        "update_state_priority",
        "get_state",
        "update_raw_availability",
        "update_availability_windows",
        "check_availability",
        "book_appointment",
        "find_technician",
        "get_current_timestamp",
        "save_service_request",
    ]

    loaded_tool_ids = _load_tool_ids()
    tool_ids = [UPDATE_STATE_INTAKE_TOOL_ID]
    for label in optional_tool_labels:
        tool_ids += _optional_tool_id(loaded_tool_ids, label)

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
    print(f"Combined prompt length: {len(prompt)} characters.")


if __name__ == "__main__":
    main()
