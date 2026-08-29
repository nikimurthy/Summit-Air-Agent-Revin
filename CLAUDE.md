# Claude Code Instructions

## Project

This repository contains the Summit Air AI phone agent take-home project.

The goal is to build a working inbound HVAC phone agent quickly while keeping the architecture simple, understandable, and easy to explain.

## Development Approach

Do not implement functionality, create or delete files, or make modifications unless explicitly requested.

Work incrementally. Each request will specify the feature or change to implement and any relevant architecture decisions. Do not stray from those instructions.

If you think there is a better solution than the one requested, explain why and ask for permission before implementing it.

Do not create folders, abstractions, helper layers, frameworks, or configuration files without my permission or solely because they may be useful later.

Before making changes, inspect the existing implementation and make sure the change is consistent with existing architecture and business rules.

## Current Architecture Decisions

- Python
- SQLite using Python's built-in `sqlite3`
- Plain SQL
- No SQLAlchemy or other ORM
- Three demo counties:
  - County Alpha
  - County Bravo
  - County Charlie
- 40 deterministic demo technicians
- Keep deterministic business and scheduling logic outside of the LLM
- Voice/LLM integration will be added after deterministic scheduling works

Do not change these decisions without my permission.

## Coding Rules

- Do not add external dependencies without first explaining why they are needed and getting permission.
- Prefer Python standard-library functionality when practical.
- Keep SQL explicit and readable.
- Use deterministic code for business rules, validation, scheduling, and database operations.
- Use the LLM primarily for understanding the caller and managing the conversation.
- Avoid unnecessary abstraction.
- Do not modify unrelated files.
- Do not implement functionality for potential future needs unless requested.
- Do not make Git commits.
- Do not push to GitHub.
- With VAPI integration, ensure that prompts and tool-calling is done via API in local repo, rather than configured on VAPI UI dashboard

## Before Implementing

For any meaningful change:

1. State which files you intend to create or modify.
2. Briefly explain why each change is necessary.
3. State any assumptions you need to make.
4. Keep the proposed scope limited to the requested feature.

## After Implementing

1. Summarize what was added or changed.
2. Explain any important implementation decisions.
3. Provide the exact commands needed to run or test the change.
4. Verify the change works before considering the task complete.
5. Report any known limitations or assumptions.
6. Do not commit the changes.

## Scope Discipline

The priority is to reach a reliable, working phone-call experience quickly.

When deciding between additional backend sophistication and getting the complete agent workflow working, prioritize the end-to-end agent unless the additional complexity is necessary for correctness, reliability, or safety.