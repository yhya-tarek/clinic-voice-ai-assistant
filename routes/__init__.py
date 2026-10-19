"""
Routes module for FastAPI endpoints.
"""

from .call_routes import index_page, handle_incoming_call, update_instructions
from .websocket_handler import handle_media_stream
from .verification_routes import (
    verification_page,
    send_verification_code,
    verify_code,
    SendVerificationRequest,
    VerifyCodeRequest
)

__all__ = [
    "index_page",
    "handle_incoming_call",
    "update_instructions",
    "handle_media_stream",
    "verification_page",
    "send_verification_code",
    "verify_code",
    "SendVerificationRequest",
    "VerifyCodeRequest"
]
