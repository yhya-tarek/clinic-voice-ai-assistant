# Clinic Voice Agent

A real-time phone agent that answers a clinic's line and books, reschedules and cancels appointments in natural conversation. Callers dial a normal phone number; the agent listens, talks back with a natural voice, and writes directly to the clinic's scheduling database.

Originally built for a production deployment at a private clinic. This repository is a sanitized version: the client's name, branding, staff and infrastructure have been replaced with a fictional "Demo Health Clinic".

## What it does

- **Answers inbound calls** (and can place outbound ones) over Twilio.
- **Speaks the caller's language.** Speech recognition auto-detects the language per utterance (English and German by default, configurable), and the agent replies in whatever the caller is using, switching mid-call if they do.
- **Handles barge-in.** If the caller interrupts, playback stops immediately and the agent listens instead of talking over them.
- **Books real appointments** through LLM tool calling: registers the patient, looks up free slots by specialty and doctor working hours, books, lists past bookings, and updates or cancels them.
- **Stays in scope.** A clinic config file defines allowed and forbidden topics (no diagnoses, no medication advice, no emergency triage).
- **Admin panel** at `/` to edit the agent's instructions live and inspect patients and appointments.
- **Phone verification page** (`/verify`) using Twilio Verify (SMS or call OTP).

## Architecture

```
Caller ──► Twilio ──► /incoming-call (TwiML) ──► WS /media-stream
                                                     │
          ┌──────────────────────────────────────────┼──────────────────────────┐
          ▼                                          ▼                          ▼
  Azure Speech (STT)                     Azure OpenAI Realtime          Cartesia (TTS)
  μ-law 8 kHz push stream,               instructions + tool schemas,   streaming μ-law audio
  continuous language ID,                function calling               back to Twilio,
  silence-based segmentation                     │                      interruptible
                                                 ▼
                                      tools/ ──► PostgreSQL
                                      (patients, doctors, working hours, bookings)
```

The pipeline is fully streaming: audio frames from Twilio are pushed into the recognizer as they arrive, recognized text is sent to the model as soon as the caller pauses, and TTS audio is streamed back chunk by chunk. An interruption event cancels the in-flight model response and TTS stream and clears Twilio's playback buffer. See [ARCHITECTURE.md](ARCHITECTURE.md) for module-level detail.

## Project layout

```
main.py                    FastAPI app and endpoints
config.py                  Environment and constants
clinic_config.json         Clinic facts the agent may talk about (fictional)
instructions.txt           Agent persona and booking flow (editable from the admin panel)
database.py                PostgreSQL schema and queries (ClinicDB)
routes/
  websocket_handler.py     Real-time media stream: STT → LLM → TTS, interruptions
  call_routes.py           TwiML for incoming calls, admin panel
  verification_routes.py   OTP verification page and API
services/
  speech_service.py        Azure Speech configuration
  openai_service.py        Realtime session setup
  tts_service.py           Cartesia streaming TTS
  twilio_verify_service.py Twilio Verify wrapper
tools/
  schemas.py               Function-calling schemas
  implementations.py       Tool → database bindings
```

## Agent tools

| Tool | Purpose |
|---|---|
| `add_new_patient` | Register the caller (name, phone) |
| `check_available_appointments` | Free slots by specialty, from doctor working hours minus existing bookings |
| `book_appointment` | Book a chosen slot |
| `check_previous_appointments` | List the caller's bookings by phone number |
| `update_appointment` | Reschedule, change doctor, or cancel |
| `get_date` | Current date, so relative dates ("next Tuesday") resolve correctly |

## Running it

Requirements: Python 3.12+, PostgreSQL, and accounts for Twilio, Azure OpenAI (realtime-capable deployment), Azure Speech and Cartesia.

```bash
pip install -r requirements.txt     # or: uv sync
cp .env.example .env                # fill in your keys

# create the schema (drops existing tables!) and add a doctor with working hours
python -c "
from datetime import time
from database import ClinicDB
db = ClinicDB(); db.setup_database()
doc = db.add_doctor('Dr. Jane Doe', specialty='General Practice')['data']['doctor_id']
for day in range(1, 6): db.add_worktime(doc, day, time(9), time(17))  # Mon-Fri (0 = Sunday)
"

python main.py                      # serves on $PORT (default 8080)
```

Expose the service over HTTPS (e.g. ngrok or a cloud host) and set your Twilio number's voice webhook to `https://<your-host>/incoming-call`.

To adapt it to another clinic, edit `clinic_config.json` and `instructions.txt`; set `SPEECH_LANGUAGES` for the languages your callers speak.

## Stack

Python · FastAPI · WebSockets · Twilio Media Streams & Verify · Azure OpenAI Realtime · Azure Speech · Cartesia · PostgreSQL
