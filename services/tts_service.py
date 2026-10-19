"""
Text-to-Speech service using Cartesia.
Handles conversion of text to audio for voice responses.
"""

import os
import base64
from cartesia import Cartesia
from config import  CARTESIA_API_KEY,CARTESIA_VOICE_ID, CARTESIA_MODEL_ID, CARTESIA_OUTPUT_FORMAT
import websockets
import asyncio
import logging
import json
logger = logging.getLogger(__name__)

class CartesiaTTSService:
    """Service for text-to-speech conversion using Cartesia."""

    def __init__(self):
        """Initialize the Cartesia TTS service."""
        self.client = None
        self.websocket = None
        self.current_stream_stopped = asyncio.Event()

    @property
    def is_closed(self):
        """Safely check if the websocket is closed (works with raw websockets.connect)"""
        return (hasattr(self.websocket, 'close_code') and
                self.websocket.close_code is not None)

    def stop_current_stream(self):
        """Signal that the current audio stream should stop immediately."""
        self.current_stream_stopped.set()
        logger.info("🛑 Signal sent to stop current TTS stream")

    async def initialize(self):
        """Connect to Cartesia TTS service."""
        if not CARTESIA_API_KEY:
            raise RuntimeError("CARTESIA_API_KEY is not set")
        # self.client = Cartesia(api_key=CARTESIA_API_KEY)
        # self.websocket = self.client.tts.websocket()
        self.websocket = await websockets.connect(
            f"wss://api.cartesia.ai/tts/websocket?api_key={CARTESIA_API_KEY}&cartesia_version=2024-11-13",

        )
        
        print("✅ Connected to Cartesia TTS")

    async def speak(self, text: str, stream_sid: str, websocket, interruption_event: asyncio.Event = None) -> None:
        """
        Convert text to speech and stream to Twilio.

        Args:
            text: Text to convert to speech
            stream_sid: Twilio stream session ID
            websocket: WebSocket connection to Twilio
            interruption_event: Optional event to signal interruption (stops streaming early)
        """
        # Reset the stop signal for this new stream
        self.current_stream_stopped.clear()

        if self.websocket is None or getattr(self.websocket, 'close_code', None) is not None:
            logger.info("Cartesia WebSocket not connected or closed – reconnecting")
            await self.initialize()

        # Generate audio chunks from Cartesia
        await self.websocket.send(json.dumps({
            "context_id": "clinic-voice-agent",
            "model_id": CARTESIA_MODEL_ID,
            "voice": {"mode": 'id', "id": CARTESIA_VOICE_ID},
            "transcript": text,
            "stream": True,
            "output_format": CARTESIA_OUTPUT_FORMAT
        }))

        interrupted = False
        try:
            async for audio_chunk in self.websocket:
                # Check for interruption before processing/sending each chunk
                if (interruption_event and interruption_event.is_set()) or self.current_stream_stopped.is_set():
                    logger.info("🛑 Interruption detected - stopping Cartesia audio stream immediately")
                    interrupted = True
                    break

                data = json.loads(audio_chunk)
                if data.get("type") == "chunk":
                    # Double-check interruption before sending
                    if (interruption_event and interruption_event.is_set()) or self.current_stream_stopped.is_set():
                        logger.info("🛑 Interruption detected - discarding audio chunk")
                        interrupted = True
                        break

                    audio_b64 = data["data"]
                    audio_delta = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": audio_b64},
                    }
                    await websocket.send_json(audio_delta)
                elif data.get("type") == "done":
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info("🛑 Cartesia WebSocket closed unexpectedly")
            interrupted = True
        finally:
            # Only send empty payload if we completed normally (not interrupted)
            if not interrupted and not self.is_closed:
                # Send empty payload to signal end of audio
                audio_delta = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": ""},
                }
                logger.info("✅ Cartesia TTS completed normally")
                await websocket.send_json(audio_delta)
            elif interrupted:
                logger.info("🛑 Cartesia TTS was interrupted - no end marker sent")

            # Reconnect if websocket was closed
            if self.is_closed:
                logger.info("Cartesia WebSocket was closed – reinitializing for next use")
                await self.initialize()  # Reconnect for future speaks
           


# Global instance
cartesia_service = CartesiaTTSService()
