# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INCOMING CALL                            │
│                         (Twilio)                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                      │  │
│  │  • GET /                → Status page                     │  │
│  │  • POST /incoming-call  → TwiML response                  │  │
│  │  • WS /media-stream     → Real-time audio processing      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    routes/websocket_handler.py                   │
│                   MediaStreamHandler Class                       │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ receive_from_   │  │ process_        │  │ send_to_        │ │
│  │ twilio()        │  │ recognized_     │  │ twilio()        │ │
│  │                 │  │ text()          │  │                 │ │
│  │ Audio → STT     │  │ Text → OpenAI   │  │ Response → TTS  │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                     │          │
└───────────┼────────────────────┼─────────────────────┼──────────┘
            │                    │                     │
            ▼                    ▼                     ▼
┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│ services/         │  │ services/         │  │ services/        │
│ speech_service.py │  │ openai_service.py │  │ tts_service.py   │
│                   │  │                   │  │                  │
│ Azure STT         │  │ Azure OpenAI      │  │ Cartesia TTS     │
│ • Configure       │  │ • Session init    │  │ • Text→Audio     │
│ • Recognize       │  │ • Tool calling    │  │ • Stream audio   │
│ • Callbacks       │  │ • Conversation    │  │                  │
└───────────────────┘  └─────────┬─────────┘  └──────────────────┘
                                 │
                                 │ Uses Tools
                                 ▼
                       ┌───────────────────┐
                       │ tools/            │
                       │ implementations   │
                       │                   │
                       │ • add_patient     │
                       │ • check_slots     │
                       │ • book            │
                       │ • check_previous  │
                       │ • update          │
                       │ • get_date        │
                       └─────────┬─────────┘
                                 │
                                 │ Calls DB
                                 ▼
                       ┌───────────────────┐
                       │ database.py       │
                       │                   │
                       │ PostgreSQL        │
                       │ • Patients        │
                       │ • Doctors         │
                       │ • Appointments    │
                       │ • Availability    │
                       └───────────────────┘
```

## Data Flow

### 1. **Incoming Call Flow**
```
Twilio Call → /incoming-call → TwiML Response → WebSocket /media-stream
```

### 2. **Audio Processing Flow**
```
Twilio Audio (mulaw)
    ↓
Azure Speech SDK (STT)
    ↓
Recognized Text
    ↓
Azure OpenAI (Conversation AI)
    ↓ (may trigger tools)
Tool Execution → Database
    ↓
AI Response Text
    ↓
Cartesia TTS
    ↓
Audio Stream (mulaw)
    ↓
Twilio → User
```

### 3. **Tool Execution Flow**
```
OpenAI generates tool call
    ↓
tools/implementations.py
    ↓
database.py (ClinicDB)
    ↓
PostgreSQL
    ↓
Result returned to OpenAI
    ↓
OpenAI generates natural language response
```

## Module Responsibilities

### **config.py**
- Environment variable loading
- Application constants
- Service configurations
- Clinic settings

### **main.py**
- FastAPI app initialization
- Route registration
- Application entry point

### **routes/**

#### **call_routes.py**
- HTTP endpoints
- Status page HTML
- TwiML response generation

#### **websocket_handler.py**
- WebSocket connection management
- Audio stream coordination
- Service orchestration
- Interruption handling

### **services/**

#### **speech_service.py**
- Azure STT configuration
- Audio format setup
- Speech recognizer creation

#### **tts_service.py**
- Cartesia TTS initialization
- Text-to-speech conversion
- Audio streaming to Twilio

#### **openai_service.py**
- OpenAI session configuration
- System instructions
- Tool registration

### **tools/**

#### **schemas.py**
- Function definitions for AI
- Parameter specifications
- Tool descriptions

#### **implementations.py**
- Tool business logic
- Database interactions
- Response formatting

### **database.py**
- PostgreSQL connection
- CRUD operations
- Appointment management
- Availability queries

## Configuration Files

### **clinic_config.json**
- Clinic information
- Service areas
- Allowed/forbidden topics
- Business rules

### **.env**
- API keys and secrets
- Database credentials
- Service endpoints

## Concurrency Model

The application uses `asyncio.gather()` to run three concurrent tasks:

1. **receive_from_twilio()**: Continuous audio ingestion and STT
2. **process_recognized_text()**: Utterance detection and OpenAI submission
3. **send_to_twilio()**: Response handling and TTS output

This allows for:
- Real-time audio processing
- Simultaneous speech recognition
- Immediate response generation
- User interruption detection

## Error Handling

Each layer handles its own errors:

- **WebSocket layer**: Connection failures, disconnects
- **Service layer**: API errors, timeout handling
- **Tool layer**: Database errors, validation failures
- **Database layer**: Query errors, constraint violations

## Security Considerations

- Environment variables for all secrets
- No hardcoded credentials
- Input validation in tool implementations
- Database connection pooling
- Proper error messages (no secret leakage)

## Performance Optimizations

- Streaming TTS (no buffering delay)
- Continuous STT (no chunking lag)
- Concurrent task execution
- Efficient silence detection (1.5s threshold)
- Database connection reuse

## Extensibility Points

### Adding a New Tool
1. Add schema to `tools/schemas.py`
2. Add implementation to `tools/implementations.py`
3. Register in `TOOL_IMPLEMENTATIONS`

### Adding a New Service
1. Create new file in `services/`
2. Export from `services/__init__.py`
3. Use in `websocket_handler.py`

### Adding a New Route
1. Add function to `routes/call_routes.py`
2. Register in `main.py`

### Changing TTS/STT Provider
1. Create new service in `services/`
2. Swap in `websocket_handler.py`
3. Update config in `config.py`
