"""
Configuration module for the Clinic Voice Agent.
Loads environment variables and application constants.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_API_ENDPOINT")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# Azure Speech Configuration
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION", "westeurope")

# Languages the caller may speak (auto-detected per utterance)
SPEECH_LANGUAGES = [l.strip() for l in os.getenv("SPEECH_LANGUAGES", "en-US,de-DE").split(",") if l.strip()]

# Cartesia TTS Configuration
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "clinic_test_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres")
}

# Application Configuration
PORT = int(os.getenv("PORT", 8080))
# Public https URL of this service (used for outbound calls)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
VOICE = "alloy"

# Speech Recognition Configuration
# SPEECH_RECOGNITION_LANGUAGE = "de-DE"
SEGMENTATION_SILENCE_TIMEOUT_MS = "1000"
SILENCE_THRESHOLD_SECONDS = 1.5

# Audio Format Configuration (Twilio)
TWILIO_AUDIO_FORMAT = {
    "samples_per_second": 8000,
    "bits_per_sample": 8,
    "channels": 1
}

# Cartesia TTS Configuration
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID")
CARTESIA_MODEL_ID = "sonic-3"
CARTESIA_OUTPUT_FORMAT = {
    "container": "raw",
    "encoding": "pcm_mulaw",
    "sample_rate": 8000
}

# OpenAI Configuration
OPENAI_TEMPERATURE = 0.7
MAX_RESPONSE_WORDS = 15

# Twilio Verify Service Configuration
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")

# Load clinic configuration
def load_clinic_config():
    """Load clinic configuration from JSON file."""
    path = os.getenv("CLINIC_CONFIG_PATH", os.path.join(os.path.dirname(__file__), "clinic_config.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CLINIC_CONFIG = load_clinic_config()
