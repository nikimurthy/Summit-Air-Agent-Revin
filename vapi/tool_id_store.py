"""Shared helpers for creating Vapi tools and recording their ids.

All tool ids live in one shared file, vapi/tools/tool_ids.txt, one line per
tool as "<label> id: <uuid>". publish_prompts.py reads from this same file.
"""
import json
import os
import urllib.request

TOOL_IDS_PATH = "vapi/tools/tool_ids.txt"


def read_api_key() -> str:
    with open(os.path.expanduser("~/.vapi-cli.yaml")) as f:
        for line in f:
            if line.startswith("api_key:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("api_key not found in ~/.vapi-cli.yaml")


def existing_tool_id(label: str) -> str | None:
    if not os.path.exists(TOOL_IDS_PATH):
        return None
    for line in open(TOOL_IDS_PATH):
        existing_label, sep, tool_id = line.strip().partition(" id: ")
        if sep and existing_label.strip() == label:
            return tool_id.strip()
    return None


def create_tool(label: str, body: dict) -> str:
    """POSTs body to /tool, appends '<label> id: <id>' to tool_ids.txt, returns the new id.

    Refuses to run if label already has an entry, to avoid creating a duplicate tool.
    """
    existing = existing_tool_id(label)
    if existing is not None:
        raise SystemExit(
            f"'{label}' already has an id in {TOOL_IDS_PATH} ({existing}). "
            "Delete that line (and the tool on Vapi's side, if it exists) before re-running, "
            f"to avoid creating a duplicate {label} tool."
        )

    request = urllib.request.Request(
        "https://api.vapi.ai/tool",
        method="POST",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "summit-air-agent/1.0",
        },
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)

    _append_line(f"{label} id: {result['id']}")

    return result["id"]


def _append_line(line: str) -> None:
    #guard against appending onto a file that doesn't already end in a newline
    needs_leading_newline = (
        os.path.exists(TOOL_IDS_PATH)
        and os.path.getsize(TOOL_IDS_PATH) > 0
        and not open(TOOL_IDS_PATH).read().endswith("\n")
    )
    with open(TOOL_IDS_PATH, "a") as f:
        if needs_leading_newline:
            f.write("\n")
        f.write(line + "\n")


def update_tool(label: str, body: dict) -> str:
    """PATCHes the existing tool recorded under label with body, returns its id.

    Refuses to run if label has no existing entry — use create_tool for that.
    """
    existing = existing_tool_id(label)
    if existing is None:
        raise SystemExit(
            f"'{label}' has no id in {TOOL_IDS_PATH} — nothing to update. "
            "Use create_tool to create it first."
        )

    body = dict(body)
    body.pop("type", None)  # immutable on an existing tool

    request = urllib.request.Request(
        f"https://api.vapi.ai/tool/{existing}",
        method="PATCH",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "summit-air-agent/1.0",
        },
    )
    with urllib.request.urlopen(request) as response:
        json.load(response)

    return existing
