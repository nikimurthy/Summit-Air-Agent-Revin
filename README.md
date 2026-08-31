# Summit Air Agent – Revin

## Quickstart

**Call the live agent:** [743-902-8235](tel:7439028235)

**Live backend:** deployed on Render at `https://summit-air-agent-revin.onrender.com` (runs `agent.py`, no laptop required). Vapi assistant id: `75bb9109-bb9a-460d-8fcd-3545a6484358`.

### Run locally

```
pip install -r requirements.txt
python3 -m db.reset_database          # seeds 40 technicians
python3 -m db.set_sample_database     # seeds sample appointments + service requests
python3 agent.py                      # starts the Flask webhook server on port 5001
```

The local server only receives tool-call webhooks from Vapi — it isn't reachable by Vapi unless it's tunneled (e.g. ngrok) or deployed somewhere public (e.g. Render, as above).

### Switching between local and Render

Which backend actually handles a call is decided entirely by whatever URL is currently set on each tool's `server.url` field on Vapi — it has nothing to do with which process is running. Render keeps running independently either way (it doesn't stop or pause just because you start `agent.py` locally), so switching to local for testing and back to Render afterward is just a matter of re-pointing the tools, not starting/stopping either deployment.

**Switch to local (ngrok):**
1. `python3 agent.py` — start the local Flask server (port 5001)
2. `ngrok http 5001 --url=https://supplier-douche-recognize.ngrok-free.dev` — reattach to the reserved ngrok domain (in a separate terminal)
3. In each `vapi/tools/*.json`, change `server.url` from the Render URL to `https://supplier-douche-recognize.ngrok-free.dev/vapi/tool-calls`
4. Push each changed tool to Vapi:
   ```
   for label in get_new_requestID update_state_intake request_human_escalation get_state \
                update_state_priority update_raw_availability update_availability_windows \
                check_availability book_appointment find_technician get_current_timestamp \
                save_service_request get_scheduling_config; do
     python3 vapi/update_tool.py "$label"
   done
   ```
5. Test — your local terminal and `summit_air.db` will now reflect the call.

**Switch back to Render:**
1. In each `vapi/tools/*.json`, change `server.url` back to `https://summit-air-agent-revin.onrender.com/vapi/tool-calls`
2. Re-run the same `update_tool.py` loop from step 4 above
3. You can stop the local `agent.py`/ngrok processes — Render is already running and will pick calls back up immediately

### Push config changes to Vapi

All prompts and tool definitions are config-as-code under `vapi/` — never edited in the Vapi dashboard. Requires a Vapi API key in `~/.vapi-cli.yaml`:

```yaml
api_key: "<your Vapi API key>"
```
After editing a phase prompt (`vapi/prompts/*.md`) or `vapi/prompts/first_message.txt`:   python3 vapi/publish_prompts.py

After editing an existing tool's definition (`vapi/tools/<label>.json`): python3 vapi/update_tool.py <label>

To add a brand-new tool for the first time:  python3 vapi/create_tool.py <label>
(records the new tool's id in `vapi/tools/tool_ids.txt`, which `publish_prompts.py` reads automatically)

**Never click Publish in the Vapi dashboard** — it reverts to stale cached content. The scripts above are the only source of truth.

## About

Summit Air Agent is an AI voice agent for a fictional HVAC company with 40 technicians across three counties. The agent handles inbound calls, identifies the caller's needs, and books an appropriate service appointment.

The agent:
- Identifies the HVAC issue and its priority
- Determines residential vs. commercial
- Collects the caller's name, address, and availability
- Finds and books an appropriate technician
- Escalates calls to a human when necessary

## Agent Workflow

1. **Intake**
   - Collect caller information, service location, and HVAC issue.
   - Determine whether the request can be handled by the automated workflow.

2. **Assess Priority**
   - Classify the issue as Routine, Urgent, or Emergency.
   - Emergencies are immediately escalated to a human.

3. **Schedule**
   - Collect the caller's availability.
   - Find an appropriate technician and appointment based on priority and service area.
   - Offer and book a confirmed appointment.
   - Escalate to a human if automated scheduling cannot be completed.

4. **Complete**
   - Save the service request and summarize the outcome.
   - Handle any additional service requests before ending the call.

## Priority Rules

### Routine
- Search technicians in the caller's county first.
- Search local availability in 2-3 week increments
- If none is available, expand the search to all technicians.
- All bookings must have 30 minute buffers before and after when compared to other bookings

### Urgent
- Search all technicians for the earliest appointment compatible with the caller's availability.
- No-buffer booking
- Search availability in 1-2 day increments

### Emergency
- Trigger human escalation immediately

## Demo Features

- **40 technicians** across 3 service areas: County Alpha, County Bravo, and County Charlie
- **Business hours:** Monday–Friday, 8 AM–5 PM (`config.py`: `BUSINESS_DAYS`, `BUSINESS_START_HOUR`, `BUSINESS_END_HOUR`)
- **Appointments:** 30 minutes each, always starting on the hour or half-hour (`APPOINTMENT_DURATION_MINUTES`)
- **Routine requests:** restricted to the caller's own county, require a 30-minute buffer before/after any other booking for that technician, and search up to 14 days out (`BUFFER_MINUTES`, `ROUTINE_BOOKING_WINDOW_DAYS`)
- **Urgent/Emergency requests:** all technicians are eligible (no buffer required), search up to 7 days out — the caller's own county is preferred as a tiebreak among otherwise-equal slots, but never restricts eligibility (`URGENT_BOOKING_WINDOW_DAYS`)
- **`get_scheduling_config`** exposes all of the above business rules to the agent directly, so none of it is hardcoded into the prompt
- **Multiple service requests per call:** each request gets its own `requestID` (from `get_new_requestID`), so one phone call can gather info, book, and start over for a second unrelated issue without the two getting mixed up
- **Human escalation** is mocked for the demo, and comes in two forms: an immediate request (e.g. emergency, gas smell) vs. a business-hours callback request (e.g. caller asks for a human, or the request can't be resolved automatically)
- Escalation is also triggered automatically after `MAX_BOOKING_FAILURES` (3) failed booking attempts in a row
- One issue that exists across multiple locations in different counties is treated as a separate request per location, requiring separate bookings
- Every service request — complete or not, booked or not — is durably saved to the `service_requests` table via `save_service_request`, so partial/abandoned calls are still recorded

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

All tools are defined as config-as-code in `vapi/tools/*.json` and handled in `agent.py`, which dispatches to the deterministic business logic in `tools.py`. The agent calls the LLM primarily to understand the caller and orchestrate which tool to call next — every scheduling/validation/database decision happens in plain Python, not the model.

**Request lifecycle**
- `get_new_requestID` — starts a new service request; returns the `requestID` used on every subsequent call for this request
- `update_state_intake` — records caller info (name, phone, address, county, property type, issue) as it comes in
- `update_state_priority` — records the assessed priority (routine/urgent/emergency), advancing to scheduling
- `get_state` — returns everything currently known about a request, given its `requestID`
- `save_service_request` — persists the request's current state to the database, at any level of completeness

**Scheduling**
- `get_current_timestamp` — the real current date/time, so the agent can resolve relative dates ("tomorrow", "next Tuesday")
- `get_scheduling_config` — business rules the agent needs for scheduling: appointment duration, buffer time, business hours/days, booking windows, and max booking failures
- `update_raw_availability` — appends the caller's own words about availability to a running log
- `update_availability_windows` — saves the caller's availability as structured time windows (replaces the full set each call)
- `check_availability` — finds the earliest slot matching the request's priority, county, and availability
- `book_appointment` — books the exact slot the caller confirmed; fails if it was taken since being offered
- `find_technician` — looks up a technician's name/county by id, for confirming bookings to the caller

**Escalation**
- `request_human_escalation` — alerts a human, either immediately (emergency) or as a business-hours callback

**Predefined**
- `endCall` — Vapi's built-in tool for ending the call once the conversation is complete

## Building Plan
- Build sample database
- Build tool calling mechanisms
- Connect VAPI AI
- Define all prompts
- Test all edge cases & implement random seed database generation
- Display results on terminal

## Real World Considerations / Future Updates:
- lookup_appointment
- If book_appt fails and another check_availbility is run, it could return same time but different technician ID, which is strange -> make check_availability return list of openings for a certain time?
- Better request ID creation / better handling of multiple requests in one call
- Implement technician latitude/longitude to find closest one
- Human Escalation functionality 
- Appointment schuduling that exists beyond half-hour marks
- Handle multi-location issues
- Add specific technician availability rather than assuming all technicians are available outside appointment slots
- Change check_availability logic to loop through 30-min increments of the availability slots
- How quickly should it enable human escalation if requested immediately?
- Configure each phase to be performed by a different agent and pass state information rather than sharing it
- Duplicate call detection via prelimiary appointment checking for past/future appointments with same caller


## Cases to test for
- Calling about multiple issues at once
- Caller unsure if commericial or residential
- Providing schedule before asked by agent
- Change appointment slot time to something other than 30 min
