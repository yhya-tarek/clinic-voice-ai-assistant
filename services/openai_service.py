"""
OpenAI service for AI conversation handling.
Manages session initialization and configuration.
"""

import json
import logging
from config import CLINIC_CONFIG, OPENAI_TEMPERATURE, MAX_RESPONSE_WORDS
from tools import TOOL_SCHEMAS

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for managing Azure OpenAI Realtime API sessions."""

    @staticmethod
    def _read_instructions():
        """Read instructions from the instructions.txt file."""
        import os
        instructions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instructions.txt")
        try:
            with open(instructions_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("instructions.txt not found, using default instructions")
            return """you are Clara, the human-like appointment-booking assistant for the clinic."""

    @staticmethod
    async def initialize_session(openai_ws):

        """
        Initialize the Azure OpenAI session with instructions and tools.

        Args:
            openai_ws: WebSocket connection to Azure OpenAI
        """
        instructions_template = OpenAIService._read_instructions()
        instructions = instructions_template.replace("{CLINIC_CONFIG}", str(CLINIC_CONFIG))

        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": instructions,
                "temperature": OPENAI_TEMPERATURE,
                "tools": TOOL_SCHEMAS,
                "tool_choice": "auto",
            },
        }

        await openai_ws.send(json.dumps(session_config))
        logger.info("Azure OpenAI session initialized")
