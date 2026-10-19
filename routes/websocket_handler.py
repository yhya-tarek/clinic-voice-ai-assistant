"""
WebSocket handler for Twilio media streams.
Manages real-time audio processing and conversation flow.
"""

import json
import base64
import asyncio
import logging
import websockets
import azure.cognitiveservices.speech as speechsdk
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_ENDPOINT, SILENCE_THRESHOLD_SECONDS
from services import AzureSpeechService, cartesia_service, OpenAIService
from tools import TOOL_IMPLEMENTATIONS

logger = logging.getLogger(__name__)


class MediaStreamHandler:
    """Handles WebSocket media stream from Twilio and coordinates all services."""

    def __init__(self, websocket: WebSocket):
        """
        Initialize the media stream handler.

        Args:
            websocket: WebSocket connection from Twilio
        """
        self.websocket = websocket
        self.stream_sid = None
        self.interruption_event = asyncio.Event()
        self.buffer_cleared_event = asyncio.Event()
        self.loop = asyncio.get_running_loop()
        # Speech recognition state
        self.complete_text = []
        self.is_recognizing = False
        self.agent_playback_active = False  # True when audio is being sent OR playing in Twilio buffer
        self.current_speech_mark = None  # Track the current speech end mark
        self.should_cancel_response = False
        self.mark_events = {}

        # Service instances
        self.speech_recognizer = None
        self.push_stream = None
        self.openai_ws = None

    async def handle_stream(self):
        """Main entry point for handling the media stream."""
        logger.info("WebSocket connection opened.")
        await self.websocket.accept()

        # Initialize speech recognition
        speech_config = AzureSpeechService.create_speech_config()
        self.push_stream, audio_config = AzureSpeechService.create_push_stream()
        self.speech_recognizer = AzureSpeechService.create_speech_recognizer(
            speech_config, audio_config
        )

        # Azure OpenAI connection headers
        headers = {
            "api-key": AZURE_OPENAI_API_KEY,
            "Authorization": f"Bearer {AZURE_OPENAI_API_KEY}"
        }

        # Connect to Azure OpenAI and process stream
        async with websockets.connect(
            AZURE_OPENAI_API_ENDPOINT,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
        ) as openai_ws:
            self.openai_ws = openai_ws
            logger.info(f"Connected to Azure OpenAI WebSocket: {AZURE_OPENAI_API_ENDPOINT}")

            # Initialize OpenAI session
            await OpenAIService.initialize_session(openai_ws)

            # Initialize Cartesia TTS
            await cartesia_service.initialize()

            # Run all concurrent tasks
            await asyncio.gather(
                self._receive_from_twilio(),
                self._process_recognized_text(),
                self._send_to_twilio()
            )

    async def _cancel_response(self):
        """Cancel the current AI response when user interrupts and stop agent speech immediately."""
        if self.agent_playback_active:
            self.should_cancel_response = True
            self.agent_playback_active = False  # Immediately mark as inactive
            self.interruption_event.set()  # Signal interruption for TTS to stop

            # Cancel any pending speech end mark tracking
            if self.current_speech_mark and self.current_speech_mark in self.mark_events:
                del self.mark_events[self.current_speech_mark]
                self.current_speech_mark = None

            logger.info("⚠️ User interruption detected - stopping agent speech immediately")

            try:
                # Cancel ongoing OpenAI response
                cancel_message = {"type": "response.cancel"}
                if self.openai_ws and self.openai_ws.close_code is None:
                    await self.openai_ws.send(json.dumps(cancel_message))
                    logger.info("🛑 Cancelled ongoing OpenAI response generation")

                # Stop Cartesia TTS stream (signal via event, don't close the websocket)
                cartesia_service.stop_current_stream()
                logger.info("🛑 Stopped Cartesia TTS stream")

                # Clear Twilio audio buffer with mark confirmation
                if self.stream_sid and self.websocket:
                    # Clear the buffer
                    clear_message = {
                        "event": "clear",
                        "streamSid": self.stream_sid
                    }
                    await self.websocket.send_json(clear_message)

                    # Send mark to confirm buffer is cleared
                    import time
                    mark_name = f"clear_{int(time.time() * 1000)}"
                    self.mark_events[mark_name] = asyncio.Event()
                    mark_message = {
                        "event": "mark",
                        "streamSid": self.stream_sid,
                        "mark": {"name": mark_name}
                    }
                    await self.websocket.send_json(mark_message)

                    # Wait for mark confirmation with timeout
                    try:
                        await asyncio.wait_for(self.mark_events[mark_name].wait(), timeout=0.5)
                        logger.info("🧹 Twilio buffer cleared and confirmed via mark")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Mark confirmation timeout, proceeding anyway")
                    finally:
                        if mark_name in self.mark_events:
                            del self.mark_events[mark_name]

                    # Signal that buffer is cleared
                    self.buffer_cleared_event.set()

            except Exception as e:
                logger.error(f"Error canceling response: {e}")

            finally:
                # Reset event for next response
                self.interruption_event.clear()

    async def _receive_from_twilio(self):
        """Receive audio from Twilio and process with Azure STT."""
        logger.info("Starting to receive from Twilio")

        def recognized_callback(evt):
            """Handle final recognized speech."""
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = evt.result.text
                if text:
                    logger.info(f"✅ Azure STT recognized: {text}")
                    self.complete_text.append(text)
                    self.is_recognizing = False

        def recognizing_callback(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizingSpeech:
                self.is_recognizing = True
                interim_text = evt.result.text.strip()
                logger.debug(f"🎤 Recognizing: {interim_text}")

                # Cancel if user starts speaking while agent audio is playing (including Twilio buffer)
                if self.agent_playback_active and interim_text and not self.should_cancel_response:
                    logger.info(f"⚠️ User interrupted with: {interim_text}")
                    asyncio.run_coroutine_threadsafe(self._cancel_response(), self.loop)
        def canceled_callback(evt):
            """Handle recognition cancellation."""
            logger.warning(f"Recognition canceled: {evt}")
            self.is_recognizing = False

        # Connect callbacks
        self.speech_recognizer.recognized.connect(recognized_callback)
        self.speech_recognizer.recognizing.connect(recognizing_callback)
        self.speech_recognizer.canceled.connect(canceled_callback)

        # Start continuous recognition
        self.speech_recognizer.start_continuous_recognition()
        logger.info("Continuous recognition started")

        try:
            async for message in self.websocket.iter_text():
                data = json.loads(message)

                if data["event"] == "media":
                    # Get audio payload from Twilio (mulaw format)
                    audio_payload = data["media"]["payload"]
                    audio_data = base64.b64decode(audio_payload)

                    # Push audio to the stream continuously
                    self.push_stream.write(audio_data)

                elif data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    logger.info(f"Stream started with SID: {self.stream_sid}")

                elif data["event"] == "mark":
                    mark_name = data["mark"]["name"]
                    logger.debug(f"Received mark: {mark_name}")

                    # Handle speech end marks
                    if mark_name == self.current_speech_mark:
                        self.agent_playback_active = False
                        self.current_speech_mark = None
                        logger.info("✅ Agent finished speaking (confirmed by Twilio mark)")

                    # Handle general mark events
                    if mark_name in self.mark_events:
                        self.mark_events[mark_name].set()

        except WebSocketDisconnect:
            logger.warning("WebSocket disconnected by client.")
            await self._cleanup()
        except Exception as e:
            logger.error(f"Error in receive_from_twilio: {e}")
            await self._cleanup()

    async def _process_recognized_text(self):
        """Process accumulated recognized text and send to OpenAI."""
        last_recognition_time = asyncio.get_event_loop().time()

        while True:
            await asyncio.sleep(0.1)  # Check every 100ms

            current_time = asyncio.get_event_loop().time()

            # If we have text and user has stopped speaking for threshold seconds
            if (
                self.complete_text
                and not self.is_recognizing
                and (current_time - last_recognition_time) >= SILENCE_THRESHOLD_SECONDS
            ):
                # Combine all accumulated text
                full_text = " ".join(self.complete_text).strip()
                self.complete_text.clear()

                if full_text:
                    logger.info(f"📤 Sending complete utterance to OpenAI: {full_text}")

                    # Reset cancel flag when sending new user message
                    self.should_cancel_response = False

                    # Send recognized text to Azure OpenAI
                    try:
                        if self.openai_ws and self.openai_ws.close_code is None:
                            text_message = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": full_text
                                        }
                                    ]
                                }
                            }
                            await self.openai_ws.send(json.dumps(text_message))
                    except Exception as send_err:
                        logger.error(f"Error sending text to OpenAI: {send_err}")

                    # Trigger response generation
                    try:
                        if self.openai_ws and self.openai_ws.close_code is None:
                            response_create = {
                                "type": "response.create"
                            }
                            await self.openai_ws.send(json.dumps(response_create))
                    except Exception as send_err:
                        logger.error(f"Error sending to OpenAI: {send_err}")

            # Update last recognition time when text is added
            if self.complete_text:
                last_recognition_time = current_time


    async def _send_to_twilio(self):
        """Receive responses from OpenAI and send to Twilio via TTS."""
        pending_tool_calls = {}
        full_text = ''
        accumulated_text=''

        async for raw in self.openai_ws:
            data = json.loads(raw)
            typ = data.get("type")

            # TEXT STREAMING
            if typ == "response.text.delta":
                delta = data.get("delta", "")
                
                print(delta, end="", flush=True)
                full_text += delta

            elif typ == "response.text.done":
                print()  # newline after text finished

                # Wait for buffer to be cleared if we just interrupted
                if self.buffer_cleared_event.is_set():
                    logger.info("⏳ Waiting briefly for buffer clear to complete...")
                    await asyncio.sleep(0.1)  # Small delay to ensure buffer is clear
                    self.buffer_cleared_event.clear()

                # Mark that agent playback is starting
                self.agent_playback_active = True
                logger.info("🎙️ Agent starting to speak")

                # Generate unique mark for this speech
                import time
                speech_mark = f"speech_end_{int(time.time() * 1000)}"
                self.current_speech_mark = speech_mark

                try:
                    # Stream audio to Twilio
                    await cartesia_service.speak(
                        full_text,
                        self.stream_sid,
                        self.websocket,
                        interruption_event=self.interruption_event
                    )

                    # Send mark to detect when Twilio finishes playing all audio
                    if self.stream_sid and self.websocket and not self.interruption_event.is_set():
                        mark_message = {
                            "event": "mark",
                            "streamSid": self.stream_sid,
                            "mark": {"name": speech_mark}
                        }
                        await self.websocket.send_json(mark_message)
                        logger.info(f"📍 Sent end-of-speech mark: {speech_mark}")
                    else:
                        # Interrupted, so mark as inactive immediately
                        self.agent_playback_active = False
                        self.current_speech_mark = None
                        logger.info("🛑 Speech was interrupted - marked as inactive")

                except Exception as e:
                    logger.error(f"Error during speech: {e}")
                    self.agent_playback_active = False
                    self.current_speech_mark = None
                finally:
                    full_text = ''
            # # TOOL CALL ARGS (delta)
            elif typ == "response.function_call_arguments.delta":
                call_id = data.get("call_id")
                delta = data.get("delta", "")
                if call_id:
                    pending_tool_calls.setdefault(call_id, {"arguments": ""})
                    pending_tool_calls[call_id]["arguments"] += delta

            # TOOL CALL DONE → execute the tool
            elif typ == "response.function_call_arguments.done":
                name = data["name"]
                call_id = data["call_id"]
                arg_str = (
                    data.get("arguments")
                    or pending_tool_calls.get(call_id, {}).get("arguments", "")
                    or "{}"
                )
                try:
                    args = json.loads(arg_str)
                except Exception:
                    args = {}

                print(f"\n[Tool Call] → {name}{args}")

                # Execute tool
                func = TOOL_IMPLEMENTATIONS.get(name)
                if func is None:
                    result = {"error": f"Tool {name} not implemented"}
                else:
                    try:
                        result = await func(**args) or {"success": True}
                    except Exception as e:
                        result = {"error": str(e)}
                print(f"[Tool Result] ← {result}\n")

                # Send tool result back
                await self.openai_ws.send(
                    json.dumps(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": json.dumps(result, ensure_ascii=False, default=str),
                            },
                        }
                    )
                )

                # Trigger next response from model after tool result
                await self.openai_ws.send(json.dumps({"type": "response.create"}))

            elif typ == "response.output_item.done":
                # function_call item completed
                pass

            elif typ == "response.done":
                # End of this response
                if full_text.strip():
                    full_text = ""

            elif typ == "error":
                print("\n[Error]", data)

    async def _cleanup(self):
        """Clean up resources on disconnect."""
        try:
            self.speech_recognizer.stop_continuous_recognition()
            self.push_stream.close()
            self.interruption_event.clear()
        except Exception as cleanup_err:
            logger.error(f"Error during cleanup: {cleanup_err}")

        try:
            if self.openai_ws and self.openai_ws.close_code is None:
                await self.openai_ws.close()
        except Exception as ws_err:
            logger.error(f"Error closing OpenAI WebSocket: {ws_err}")


async def handle_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint handler for Twilio media streams.

    Args:
        websocket: WebSocket connection from Twilio
    """
    handler = MediaStreamHandler(websocket)
    await handler.handle_stream()
