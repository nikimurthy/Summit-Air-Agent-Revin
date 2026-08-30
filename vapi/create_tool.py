"""Creates the tool defined in vapi/tools/<label>.json and records its id.

Run once per new tool:
    python3 vapi/create_tool.py <label>

Example:
    python3 vapi/create_tool.py update_state_availability
"""
import json
import sys

from tool_id_store import create_tool


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 vapi/create_tool.py <label>")

    label = sys.argv[1]
    body = json.load(open(f"vapi/tools/{label}.json"))
    tool_id = create_tool(label, body)
    print(f"Created {label} tool: {tool_id}")
    print("Saved to vapi/tools/tool_ids.txt. publish_prompts.py will pick it up automatically.")


if __name__ == "__main__":
    main()
