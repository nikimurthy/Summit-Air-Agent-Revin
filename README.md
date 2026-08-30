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
      - IF EMERGENCY: TRIGGER HUMAN ESCALATION IMMEDIATELY
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
- Search local availability in 2 week increments
- If none is available, expand the search to all technicians.
- All bookings must have 30 minute buffers before and after when compared to other bookings

### Urgent
- Search all technicians for the earliest appointment compatible with the caller's availability.
- No-buffer booking is allowed
- Search availability in 1 week increments

### Emergency
- Trigger human escalation immediately

## Demo Assumptions

- 40 technicians
- 3 service areas: County Alpha, County Bravo, and County Charlie
- Business hours: Monday–Friday, 8 AM–5 PM
- Appointments: 30 minutes with start-times on the hour or on the half-hour
- Human escalation is mocked for the demo
- One issue that exists across multiple locations in different counties will be treated as different issues for each location, and will require different service bookings
- Customer availability for Urgent & Emergency is asked week by week
- Customer availability for Routine is asked in 2 week incremenents
- Escalation is caused by:
   - Emergency issue
   - 3 increments of unavailable bookings
- 

## Architecture

- Python — application and scheduling logic
- SQLite — technicians and appointments
- SQL / sqlite3 — database access
- VAPI Voice AI — inbound phone conversation and agent orchestration

### Database Utilities

- `database.py` — database connection and schema
- `reset_database.py` — restores 40 standard technicians and clears appointments
- `set_sample_database.py` — creates reproducible sample appointment data for testing

## Tools

Planned agent tools:

- `check_availability` — finds appointments matching caller availability and priority
- `book_appointment` — books the confirmed appointment
- `request_human_followup` — mocked human escalation

## Current Questions

- Are there specific buckets of HVAC issues that I should group by?
- Can I assume appointments will only be booked on the half hour or hour? Rather than at an arbitrary time in-between?
- How much leeway can I take with assumptions? Can I create the buffer rule for different priorities?

## Building Plan
- Build sample database
- Build tool calling mechanisms
- Connect VAPI AI
- Define all prompts
- Test all edge cases & implement random seed database generation
- Display results on terminal

## Nice to Have:
- point all conversation endings to summary phase, and implement state updates in every phase for escalation, bookings, etc. so that each phase does not need conversation ending instructions
- NEEDS TO WORK WIth MY LAPTOP CLOSED
- lookup_appointment
- Implement technician latitude/longitude to find closest one
- Add distinction for human escalation when a human is back during normal hours (no availability found, unable to decipher maintenance issue, commerical problem; maybe add another priority option which is "call-back") and human escalation that alerts someone outisde business hours for emergency situations
- Store emergency calls in a database rather than null escalate function
- Appointment schuduling that exists beyond half-hour marks
- Handle multi-location issues better
- Add database to store all call information. Use this to handle duplicate calls.
- Add specific technician availability rather than assuming all technicians are available outside appointment slots
- Change check_availability logic to loop through 30-min increments of the availability slots

## Cases to test for
- Calling about multiple issues at once
- Duplicate call about same issue
- Caller unsure if commericial or residential
- Providing schedule before asked by agent
- Change appointment slot time to something other than 30 min

## Changes made along the way
- Changed county from being stored as string to integer to minimize compare errors

## Real World Considerations
- How quickly should it enable human escalation if requested immediately?
- Storing service requests in the database for future reference or analytics
- Configure each phase to be performed by a different agent and pass state information rather than sharing it


update_caller_information
        ↓
stores understood caller data

check_availability
        ↓
reads CallState, executes scheduling policy

reject_slot
        ↓
records rejected offer / moves scheduling state

book_appointment
        ↓
reads current proposed slot + caller data

lookup_appointment
        ↓
existing appointment request

human_escalation
        ↓
uses current CallState

finalize_call
        ↓
prints summary / cleans up