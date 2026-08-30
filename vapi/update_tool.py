"""Pushes vapi/tools/<label>.json's current content to that tool on Vapi.

Run whenever a tool definition file changes, for any already-created tool:
    python3 vapi/update_tool.py <label>

Example:
    python3 vapi/update_tool.py request_human_escalation
"""
import json
import sys

from tool_id_store import update_tool


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 vapi/update_tool.py <label>")

    label = sys.argv[1]
    body = json.load(open(f"vapi/tools/{label}.json"))
    tool_id = update_tool(label, body)
    print(f"Updated {label} tool ({tool_id}).")


if __name__ == "__main__":
    main()
