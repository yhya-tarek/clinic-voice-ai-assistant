"""
Speech-to-Text service using Azure Cognitive Services.
Handles audio recognition and transcription.
"""

import azure.cognitiveservices.speech as speechsdk
from config import (
    SPEECH_KEY,
    SPEECH_REGION,
    SPEECH_LANGUAGES,
    SEGMENTATION_SILENCE_TIMEOUT_MS,
    TWILIO_AUDIO_FORMAT
)


class AzureSpeechService:
    """Service for speech recognition using Azure Cognitive Services."""

    @staticmethod
    def create_speech_config():
        """
        Create and configure Azure Speech SDK configuration.

        Returns:
            Speech configuration object
        """
        endpoint = f"wss://{SPEECH_REGION}.stt.speech.microsoft.com/speech/universal/v2"
        speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_KEY,
            endpoint=endpoint
        )
        speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, value='Continuous')

        # speech_config.speech_recognition_language = SPEECH_RECOGNITION_LANGUAGE

        # Enable detailed results for better accuracy
        speech_config.output_format = speechsdk.OutputFormat.Detailed

        # Configure for continuous recognition with silence detection
        speech_config.set_property(
            speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
            SEGMENTATION_SILENCE_TIMEOUT_MS
        )

        return speech_config

    @staticmethod
    def create_audio_format():
        """
        Create audio format configuration for Twilio streams.

        Returns:
            Audio format configuration (mulaw, 8kHz, 8-bit, mono)
        """
        return speechsdk.audio.AudioStreamFormat(
            samples_per_second=TWILIO_AUDIO_FORMAT["samples_per_second"],
            bits_per_sample=TWILIO_AUDIO_FORMAT["bits_per_sample"],
            channels=TWILIO_AUDIO_FORMAT["channels"],
            wave_stream_format=speechsdk.AudioStreamWaveFormat.MULAW
        )

    @staticmethod
    def create_push_stream():
        """
        Create a push audio stream for continuous recognition.

        Returns:
            Tuple of (push_stream, audio_config)
        """
        audio_format = AzureSpeechService.create_audio_format()
        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        return push_stream, audio_config

    @staticmethod
    def create_speech_recognizer(speech_config, audio_config):
        """
        Create a speech recognizer instance.

        Args:
            speech_config: Speech configuration
            audio_config: Audio stream configuration

        Returns:
            Speech recognizer instance
        """
        auto_detect_source_language_config = \
        speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=SPEECH_LANGUAGES)
        return speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            auto_detect_source_language_config=auto_detect_source_language_config, 
            audio_config=audio_config
        )
