# Summit Air Agent – Revin

## About

Summit Air Agent is an AI voice agent for a fictional HVAC company with 40 technicians across three counties. The agent handles inbound calls, identifies the caller's needs, and books an appropriate service appointment.

The agent:
- Identifies the HVAC issue and its priority
- Determines residential vs. commercial
- Collects the caller's name, address, and availability
- Finds and books an appropriate technician
- Escalates calls to a human when necessary

## Agent Workflow

1. Collect the required caller and service information:
   - Name
   - Address / county
   - Residential or commercial
   - HVAC issue
   - Priority: routine, urgent, or emergency
   - Availability

2. Validate that the caller's availability overlaps with Summit Air's business hours.
   - If not, explain the available hours and ask for alternative availability.
   - If the caller still cannot provide compatible availability, trigger human escalation.

3. Search for appointments according to the priority rules below.

4. Offer available appointment(s) to the caller.

5. Once the caller confirms a slot, attempt to book it.
   - If the slot is no longer available, search again. If no availability found, recollect caller availability and search once more. If no availability found still, trigger human escalation.
   - If successful, confirm the appointment and end the call.

## Priority Rules

### Routine
- Search technicians in the caller's county first.
- Search local availability within the next two weeks.
- If none is available, expand the search to all technicians.

### Urgent
- Search all technicians for the earliest appointment compatible with the caller's availability.

### Emergency
- Search all technicians for the earliest appointment compatible with the caller's availability.
- Trigger human escalation.

## Demo Assumptions

- 40 technicians
- 3 service areas: County Alpha, County Bravo, and County Charlie
- Business hours: Monday–Friday, 8 AM–5 PM
- Appointments: 30 minutes with a 30-minute buffer
- Human escalation is mocked for the demo

## Architecture

- Python — application and scheduling logic
- SQLite — technicians and appointments
- SQL / sqlite3 — database access
- VAPI Voice AI — inbound phone conversation and agent orchestration

### Database Utilities

- `database.py` — database connection and schema
- `reset_database.py` — restores 40 standard technicians and clears appointments
- `seed_database.py` — creates reproducible sample appointment data for testing

## Tools

Planned agent tools:

- `check_availability` — finds appointments matching caller availability and priority
- `book_appointment` — books the confirmed appointment
- `request_human_followup` — mocked human escalation

## Current Questions

- Are there specific buckets of HVAC issues that I should group by?
- Should residential and commercial calls have different scheduling behavior?
- Is it necessary to check for duplicate callers? Someone calling twice about the same issue once it has already been booked?