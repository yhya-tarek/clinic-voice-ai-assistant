"""
Twilio phone number verification service.
Uses Twilio Verify API to verify phone numbers so they can receive calls.
"""

import logging
from typing import Dict
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_VERIFY_SERVICE_SID
)

logger = logging.getLogger(__name__)


class TwilioVerifyService:
    """Service for verifying phone numbers with Twilio Verify API."""

    def __init__(self):
        """Initialize the Twilio client."""
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.verify_service_sid = TWILIO_VERIFY_SERVICE_SID

    def send_verification_code(self, phone_number: str, channel: str = "sms") -> Dict:
        """
        Send a verification code to a phone number via Twilio Verify.

        Args:
            phone_number: Phone number in E.164 format (e.g., "+491234567890")
            channel: Verification channel - "sms" or "call"

        Returns:
            Dictionary with success status and message
        """
        try:
            verification = self.client.verify.v2.services(
                self.verify_service_sid
            ).verifications.create(
                to=phone_number,
                channel=channel
            )

            logger.info(f"Verification code sent to {phone_number} via {channel}, Status: {verification.status}")

            return {
                "success": True,
                "message": f"Verification code sent to {phone_number} via {channel.upper()}",
                "status": verification.status,
                "phone_number": phone_number
            }

        except TwilioRestException as e:
            logger.error(f"Twilio error sending verification to {phone_number}: {e}")
            return {
                "success": False,
                "message": f"Failed to send verification: {e.msg}",
                "error_code": e.code
            }
        except Exception as e:
            logger.error(f"Unexpected error sending verification to {phone_number}: {e}")
            return {
                "success": False,
                "message": f"Failed to send verification: {str(e)}"
            }

    def verify_code(self, phone_number: str, code: str) -> Dict:
        """
        Verify a code for a phone number using Twilio Verify.

        Args:
            phone_number: Phone number in E.164 format
            code: Verification code entered by user

        Returns:
            Dictionary with success status and message
        """
        try:
            verification_check = self.client.verify.v2.services(
                self.verify_service_sid
            ).verification_checks.create(
                to=phone_number,
                code=code
            )

            if verification_check.status == "approved":
                logger.info(f"Phone number verified successfully: {phone_number}")
                return {
                    "success": True,
                    "message": "Phone number verified successfully with Twilio! You can now receive calls.",
                    "status": verification_check.status,
                    "phone_number": phone_number
                }
            else:
                logger.warning(f"Verification failed for {phone_number}, Status: {verification_check.status}")
                return {
                    "success": False,
                    "message": "Invalid verification code. Please try again.",
                    "status": verification_check.status
                }

        except TwilioRestException as e:
            logger.error(f"Twilio error verifying code for {phone_number}: {e}")

            # Provide user-friendly error messages
            if e.code == 60200:
                message = "Verification code has expired. Please request a new code."
            elif e.code == 60202:
                message = "Maximum verification attempts reached. Please request a new code."
            else:
                message = f"Verification failed: {e.msg}"

            return {
                "success": False,
                "message": message,
                "error_code": e.code
            }
        except Exception as e:
            logger.error(f"Unexpected error verifying code for {phone_number}: {e}")
            return {
                "success": False,
                "message": f"Verification failed: {str(e)}"
            }


# Global instance
twilio_verify_service = TwilioVerifyService()
