"""
Main entry point for the Clinic Voice Agent.

This application provides a voice-based appointment booking system
for a medical clinic. It integrates:
- Twilio for telephony
- Azure Speech Services for STT
- Azure OpenAI for conversation AI
- Cartesia for TTS
- PostgreSQL for data persistence
"""

import logging
import uvicorn
from fastapi import FastAPI, WebSocket, Request, Form
from fastapi.responses import HTMLResponse
from twilio.rest import Client
from config import (
    PORT,
    PUBLIC_BASE_URL,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
)
from routes import (
    index_page,
    handle_incoming_call,
    update_instructions,
    handle_media_stream,
    verification_page,
    send_verification_code,
    verify_code,
    SendVerificationRequest,
    VerifyCodeRequest
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Clinic Voice Agent",
    description="Real-time phone agent for clinic appointment booking",
    version="1.0.0"
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint showing service status."""
    return await index_page()


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """Handle incoming phone calls from Twilio."""
    return await handle_incoming_call(request)


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """WebSocket endpoint for Twilio media streams."""
    await handle_media_stream(websocket)


@app.get("/verify", response_class=HTMLResponse)
async def verify():
    """Phone verification page."""
    return await verification_page()


@app.post("/api/verify/send")
async def api_send_verification(request: SendVerificationRequest):
    """API endpoint to send verification code."""
    return await send_verification_code(request)


@app.post("/api/verify/check")
async def api_verify_code(request: VerifyCodeRequest):
    """API endpoint to verify code."""
    return await verify_code(request)


@app.post("/update-instructions")
async def api_update_instructions(instructions: str = Form(...)):
    """API endpoint to update AI instructions."""
    return await update_instructions(instructions)

@app.post("/make-call")
async def make_call_endpoint(to: str = Form(...)):
    """Trigger an outbound call to `to` (E.164) that connects to this agent."""
    if not PUBLIC_BASE_URL:
        return {"status": "error", "message": "PUBLIC_BASE_URL is not set"}
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=to,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{PUBLIC_BASE_URL.rstrip('/')}/incoming-call",
        )
        return {"status": "success", "call_sid": call.sid, "to": to}
    except Exception as e:
        logger.exception("Outbound call failed")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    logger.info(f"Starting Clinic Voice Agent on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
