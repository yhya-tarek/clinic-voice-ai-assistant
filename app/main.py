import os
import json
import uvicorn
import inspect
import google.generativeai as genai
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from dotenv import load_dotenv
from typing import Callable, Optional, Any, Dict
from twilio.rest import Client

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
PORT = int(os.getenv("PORT", "8080"))
DOMAIN = os.getenv("APP_URL")
if not DOMAIN:
    raise ValueError("APP_URL environment variable not set. Set it to your Azure app URL (e.g., https://myapp.azurewebsites.net).")
WS_URL = f"wss://{DOMAIN}/ws"

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise ValueError("Missing Twilio configuration: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Updated greeting to reflect the new model
WELCOME_GREETING = "Hi! I am a voice assistant powered by Twilio and Google Gemini. Ask me anything!"

# System prompt for Gemini
SYSTEM_PROMPT = """You are a helpful and friendly voice assistant. This conversation is happening over a phone call, so your responses will be spoken aloud.
Please adhere to the following rules:
1. Provide clear, concise, and direct answers.
2. Spell out all numbers (e.g., say 'one thousand two hundred' instead of 1200).
3. Do not use any special characters like asterisks, bullet points, or emojis.
4. Keep the conversation natural and engaging."""

# --- Gemini API Initialization ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash-lite',
    system_instruction=SYSTEM_PROMPT
)

sessions = {}


class VoiceCallAgent:
    def __init__(self, port: int = 8080):
        self.app = FastAPI()
        self.port = port

        self._on_call_setup: Optional[Callable] = None
        self._on_prompt_received: Optional[Callable] = None
        self._on_get_response: Optional[Callable] = None
        self._on_interrupt: Optional[Callable] = None
        self._on_call_end: Optional[Callable] = None

        # Routes (unchanged except health_check fix)
        self.app.get("/")(lambda: {"status": "VoiceCallAgent is running"})
        self.app.post("/twiml")(self.twiml_endpoint)
        self.app.websocket("/ws")(self.websocket_endpoint)
        self.app.get("/call/{phone_number}")(self.make_call_endpoint)
        self.app.get("/health")(self.health_check)  # This line stays, but method below is fixed

    # FIXED: Add 'self' to the signature explicitly
    async def health_check(self) -> Dict[str, Any]:  # ← Added return type for FastAPI docs
        return {"status": "healthy"}

    def on_call_setup(self, handler: Callable):
        """Register handler called when a call is set up. Handler receives (call_sid)"""
        self._on_call_setup = handler
        return handler

    def on_prompt_received(self, handler: Callable):
        """Register handler called when a prompt is received. Handler receives (call_sid, prompt)"""
        self._on_prompt_received = handler
        return handler

    def on_get_response(self, handler: Callable):
        """Register handler to generate response. Handler receives (call_sid, prompt) and returns text"""
        self._on_get_response = handler
        return handler

    def on_interrupt(self, handler: Callable):
        """Register handler called on interrupt. Handler receives (call_sid)"""
        self._on_interrupt = handler
        return handler

    def on_call_end(self, handler: Callable):
        """Register handler called when call ends. Handler receives (call_sid)"""
        self._on_call_end = handler
        return handler

    async def twiml_endpoint(self):
        """Endpoint that returns TwiML for Twilio to connect to the WebSocket"""
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
        <Connect>
        <ConversationRelay url="{WS_URL}" welcomeGreeting="{WELCOME_GREETING}" ttsProvider="ElevenLabs" voice="FGY2WhTYpPnrIDTdsKH5" />
        </Connect>
        </Response>"""
        return Response(content=xml_response, media_type="text/xml")

    async def make_call_endpoint(self, phone_number: str):
        """Endpoint to trigger an outbound call"""
        try:
            call = twilio_client.calls.create(
                to=phone_number,
                from_=TWILIO_PHONE_NUMBER,
                url=f"https://{DOMAIN}/twiml"
            )
            return {"status": "success", "call_sid": call.sid, "to": phone_number}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for real-time communication"""
        await websocket.accept()
        call_sid = None

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message["type"] == "setup":
                    call_sid = message["callSid"]
                    sessions[call_sid] = model.start_chat(history=[])

                    # Call your handler
                    if self._on_call_setup:
                        await self._call_handler(self._on_call_setup, call_sid)

                elif message["type"] == "prompt":
                    if not call_sid or call_sid not in sessions:
                        continue

                    user_prompt = message["voicePrompt"]

                    # Call your handler
                    if self._on_prompt_received:
                        await self._call_handler(self._on_prompt_received, call_sid, user_prompt)

                    # Get response from your handler or default
                    if self._on_get_response:
                        response_text = await self._call_handler(self._on_get_response, call_sid, user_prompt)
                    else:
                        # Default: use Gemini
                        chat_session = sessions[call_sid]
                        response = await chat_session.send_message_async(user_prompt)
                        response_text = response.text

                    # Send response back
                    await websocket.send_text(
                        json.dumps({
                            "type": "text",
                            "token": response_text,
                            "last": True
                        })
                    )

                elif message["type"] == "interrupt":
                    if self._on_interrupt:
                        await self._call_handler(self._on_interrupt, call_sid)

        except WebSocketDisconnect:
            if call_sid:
                if self._on_call_end:
                    await self._call_handler(self._on_call_end, call_sid)
                if call_sid in sessions:
                    sessions.pop(call_sid)

    async def _call_handler(self, handler: Callable, *args, **kwargs):
        """Helper to call handlers that may or may not be async"""
        if inspect.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            return handler(*args, **kwargs)

    def run(self):
        """Start the server"""
        print(f"Starting server on port {self.port}")
        print(f"WebSocket URL for Twilio: {WS_URL}")
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, workers=1)  # Use 1 worker for WebSockets; scale via Azure App Service


# Create the agent
agent = VoiceCallAgent(port=PORT)


# --- Example: Define your handlers ---
@agent.on_call_setup
def handle_call_setup(call_sid):
    print(f"Setup for call: {call_sid}")


@agent.on_prompt_received
def handle_prompt_received(call_sid, prompt):
    print(f"Processing prompt: {prompt}")


@agent.on_get_response
async def handle_get_response(call_sid, prompt):
    """Default behavior: use Gemini. Override this for custom logic."""
    chat_session = sessions[call_sid]
    response = await chat_session.send_message_async(prompt)
    print(f"Generated response: {response.text}")
    return response.text


@agent.on_interrupt
def handle_interrupt(call_sid):
    print(f"Handling interruption for call {call_sid}")


@agent.on_call_end
def handle_call_end(call_sid):
    print(f"Call ended: {call_sid}")


if __name__ == "__main__":
    agent.run()