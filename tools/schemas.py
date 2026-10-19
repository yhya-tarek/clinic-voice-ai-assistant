"""
Tool schemas for the appointment booking system.
Defines the function signatures exposed to the AI model.
"""

from typing import List, Dict, Any

# Tool schemas for Azure OpenAI function calling
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "add_new_patient",
        "description": "add new patient in our system that hasn't booked ever before",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "name of the patient"},
                "phone_no": {"type": "string", "description": "confirmation phone number to book with"},
            },
            "required": ["name", "phone_no"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_available_appointments",
        "description": "get all available appointment slots to allow the patient to book one from them",
        "parameters": {
            "type": "object",
            "properties": {
                "clinic_type": {
                    "type": "string",
                    "description": "the clinic name that the patient wants to know its available appointments",
                },
                "date": {
                    "type": "string",
                    "description": "the date to check available appointments for (DD-MM-YYYY)",
                },
            },
            "required": ["clinic_type"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "book_appointment",
        "description": "create/book an appointment that patient chose from available",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_date": {"type": "string", "description": "the appointment date to book in"},
                "patient_phone_number": {"type": "string", "description": "patient phone number"},
                "appointment_hour": {"type": "string", "description": "the appointment hour to book in"},
                "dr_id": {"type": "string", "description": "dr id that the patient want to book with"},
                "clinic_type": {"type": "string", "description": "clinic type"},
            },
            "required": ["dr_id", "appointment_date", "patient_phone_number", "appointment_hour", "clinic_type"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "check_previous_appointments",
        "description": "get appointments that were booked before to edit or discard",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_phone_number": {
                    "type": "string",
                    "description": "the patient's phone number confirmed an appointment before with",
                },
            },
            "required": ["patient_phone_number"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "update_appointment",
        "description": "update an appointment that was booked before",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "the appointment id patient want to update his booking into ",
                },
                "appointment_date": {"type": "string", "description": "the appointment date to book in"},
                "patient_phone_number": {"type": "string", "description": "patient phone number"},
                "appointment_hour": {"type": "string", "description": "the appointment hour to book in if the user wants to reschedule"},
                "status": {"type": "string", "description": "the appointment change type ['scheduled', 'confirmed', 'cancelled', 'completed', 'no-show']"},
                "dr_id": {"type": "string", "description": "dr id that the patient want to book with only for editing or rescheduling"},
                "clinic_type": {"type": "string", "description": "clinic type"},
            },
            "required": [
                "patient_phone_number",

                "appointment_id",
                "status",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_date",
        "description": "get the current date",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]
