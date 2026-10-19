"""
FastAPI routes for handling incoming calls.
"""

from fastapi import Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import os
from config import CLINIC_CONFIG

CLINIC_NAME = CLINIC_CONFIG.get("clinic", {}).get("name", "the clinic")


def _read_instructions():
    """Read instructions from the instructions.txt file."""
    instructions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instructions.txt")
    try:
        with open(instructions_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "you are Clara, the human-like appointment-booking assistant for the clinic."


def _save_instructions(content: str):
    """Save instructions to the instructions.txt file."""
    instructions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instructions.txt")
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(content)


async def index_page():
    """
    Root endpoint displaying service status, instructions editor, and database tables.

    Returns:
        HTML page showing the voice assistant status, instructions form, and data tables
    """
    from database import ClinicDB

    db = ClinicDB()

    # Fetch data
    patients_result = db.get_all_patients()
    appointments_result = db.get_all_appointments()
    instructions = _read_instructions()

    patients = patients_result.get('data', []) if patients_result['success'] else []
    appointments = appointments_result.get('data', []) if appointments_result['success'] else []

    # Build patients table HTML
    patients_rows = ""
    for p in patients:
        patients_rows += f"""
        <tr>
            <td>{p['id']}</td>
            <td>{p['name']}</td>
            <td>{p['phone_no']}</td>
        </tr>
        """

    # Build appointments table HTML
    appointments_rows = ""
    for a in appointments:
        appointments_rows += f"""
        <tr>
            <td>{a['id']}</td>
            <td>{a['patient_name']}</td>
            <td>{a['phone_no']}</td>
            <td>{a['doctor_name']}</td>
            <td>{a['specialty']}</td>
            <td>{a['appointment_date']}</td>
            <td>{a['appointment_time']}</td>
            <td><span class="status-{a['status']}">{a['status']}</span></td>
            <td>{a['notes'] or ''}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clinic Voice Assistant - Admin Panel</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Poppins', sans-serif;
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }}

            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}

            .header {{
                text-align: center;
                color: white;
                padding: 30px;
                margin-bottom: 30px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3);
            }}

            .header .mic {{
                font-size: 4rem;
                margin-bottom: 10px;
                animation: pulse 2s infinite;
            }}

            .header h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 10px;
            }}

            .header .status {{
                font-size: 1.2rem;
                opacity: 0.9;
            }}

            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
                100% {{ transform: scale(1); }}
            }}

            .section {{
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 25px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            }}

            .section h2 {{
                color: #667eea;
                margin-bottom: 20px;
                font-size: 1.8rem;
                font-weight: 600;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            .form-group label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
            }}

            .form-group textarea {{
                width: 100%;
                min-height: 300px;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 14px;
                line-height: 1.6;
                resize: vertical;
                transition: border-color 0.3s;
            }}

            .form-group textarea:focus {{
                outline: none;
                border-color: #667eea;
            }}

            .btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}

            .btn:active {{
                transform: translateY(0);
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}

            table th {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                position: sticky;
                top: 0;
            }}

            table td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e0e0e0;
            }}

            table tr:hover {{
                background-color: #f5f5f5;
            }}

            .table-container {{
                max-height: 500px;
                overflow-y: auto;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }}

            .status-scheduled {{
                background-color: #4caf50;
                color: white;
                padding: 4px 8px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 500;
            }}

            .status-cancelled {{
                background-color: #f44336;
                color: white;
                padding: 4px 8px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 500;
            }}

            .status-completed {{
                background-color: #2196f3;
                color: white;
                padding: 4px 8px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 500;
            }}

            .message {{
                padding: 12px 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                font-weight: 500;
            }}

            .message.success {{
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}

            .message.error {{
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="mic">🩺</div>
                <h1>{CLINIC_NAME} Voice Assistant</h1>
                <div class="status">Admin Control Panel</div>
            </div>

            <div class="section">
                <h2>AI Instructions Editor</h2>
                <form method="POST" action="/update-instructions">
                    <div class="form-group">
                        <label for="instructions">Edit the AI assistant instructions below:</label>
                        <textarea id="instructions" name="instructions" required>{instructions}</textarea>
                    </div>
                    <button type="submit" class="btn">Save Instructions</button>
                </form>
            </div>

            <div class="section">
                <h2>Patients Database</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Phone Number</th>
                            </tr>
                        </thead>
                        <tbody>
                            {patients_rows if patients_rows else '<tr><td colspan="3" style="text-align: center; padding: 20px;">No patients found</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>Appointments Database</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Patient Name</th>
                                <th>Phone</th>
                                <th>Doctor</th>
                                <th>Specialty</th>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Status</th>
                                <th>Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            {appointments_rows if appointments_rows else '<tr><td colspan="9" style="text-align: center; padding: 20px;">No appointments found</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


async def update_instructions(instructions: str = Form(...)):
    """
    Update the AI instructions file.

    Args:
        instructions: New instructions content from form

    Returns:
        Redirect back to index page
    """
    try:
        _save_instructions(instructions)
        return RedirectResponse(url="/?success=1", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=303)


async def handle_incoming_call(request: Request):
    """
    Handle incoming phone calls from Twilio.

    Args:
        request: FastAPI request object

    Returns:
        TwiML response to connect the call to WebSocket
    """
    response = VoiceResponse()
    response.say("Please wait while we connect your call.")

    host = request.url.hostname

    # Connect to WebSocket media stream
    connect = Connect()
    connect.stream(url=f"wss://{host}/media-stream")
    response.append(connect)

    response.say(f"Hello and welcome to {CLINIC_NAME}.")

    return HTMLResponse(content=str(response), media_type="application/xml")
