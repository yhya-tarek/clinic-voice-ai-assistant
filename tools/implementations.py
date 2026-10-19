"""
Tool implementations for the appointment booking system.
Handles the actual business logic for appointment operations.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from database import ClinicDB

# Initialize database connection
db = ClinicDB()


async def add_new_patient(name: str, phone_no: str, clinic_type: Optional[str] = None) -> dict:
    """
    Add a new patient to the system or retrieve existing patient.

    Args:
        name: Patient's full name
        phone_no: Patient's phone number
        clinic_type: Optional clinic specialty (not used in current implementation)

    Returns:
        Dictionary with patient information
    """
    print("add_new_patient")
    return db.get_or_create_patient(name=name, phone_no=phone_no)


async def check_available_appointments(clinic_type: str) -> List[Dict[str, Any]]:
    """
    Retrieve all currently available appointment slots for a specific clinic type.

    Args:
        clinic_type: The specialty/type of clinic

    Returns:
        List of available appointment slots with doctor and time information
    """
    print("check_available_appointments")
    return db.get_specialty_availability(clinic_type)


async def book_appointment(
    clinic_type: str,
    appointment_date: str,
    patient_phone_number: str,
    appointment_hour: str,
    dr_id: str,
) -> dict:
    """
    Book a new appointment for a patient in the selected time slot.

    Args:
        clinic_type: The specialty/type of clinic
        appointment_date: Date of the appointment
        patient_phone_number: Patient's phone number
        appointment_hour: Time of the appointment
        dr_id: Doctor's ID

    Returns:
        Dictionary with booking confirmation
    """
    print("book_appointment")
    return db.book_appointment(
        patient_phone_number, dr_id, appointment_date, appointment_hour
    )


async def check_previous_appointments(patient_phone_number: str) -> List[Dict[str, Any]]:
    """
    Retrieve all past and upcoming appointments for a patient by phone number.

    Args:
        patient_phone_number: Patient's phone number

    Returns:
        List of patient's appointments
    """
    print("check_previous_appointments")
    return db.my_appointments(patient_phone_number)


async def update_appointment(
    appointment_id: str,
    status: Literal["edit", "discard", "cancel"],
    patient_phone_number: str,
    clinic_type: Optional[str] = None,
    appointment_date: Optional[str] = None,
    appointment_hour: Optional[str] = None,
    dr_id: Optional[str] = None,
) -> dict:
    """
    Update (reschedule) or cancel/discard an existing appointment.

    Args:
        appointment_id: ID of the appointment to update
        status: Type of update (edit, discard, cancel)
        patient_phone_number: Patient's phone number
        clinic_type: Optional new clinic type
        appointment_date: Optional new date
        appointment_hour: Optional new time
        dr_id: Optional new doctor ID

    Returns:
        Dictionary with update confirmation
    """
    print("update_appointment")
    return db.update_appointment(
        appointment_id=appointment_id,
        phone_no=patient_phone_number,
        new_date=appointment_date,
        new_time=appointment_hour,
        new_status=status,
        new_doctor_id=dr_id,
    )


async def get_date() -> str:
    """
    Return today's current date in YYYY-MM-DD format.

    Returns:
        Current date string
    """
    print("get_date")
    return datetime.now().strftime("%Y-%m-%d")


# Tool registry mapping tool names to their implementations
TOOL_IMPLEMENTATIONS = {
    "add_new_patient": add_new_patient,
    "check_available_appointments": check_available_appointments,
    "book_appointment": book_appointment,
    "check_previous_appointments": check_previous_appointments,
    "update_appointment": update_appointment,
    "get_date": get_date,
}
