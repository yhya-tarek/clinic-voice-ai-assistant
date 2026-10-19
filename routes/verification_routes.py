"""
Phone verification routes for Twilio number verification.
Provides web interface and API endpoints for verifying phone numbers.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from services import twilio_verify_service


class SendVerificationRequest(BaseModel):
    """Request model for sending verification code."""
    phone_number: str
    channel: str = "sms"


class VerifyCodeRequest(BaseModel):
    """Request model for verifying code."""
    phone_number: str
    code: str


async def verification_page():
    """
    Render the phone verification web interface.

    Returns:
        HTML page for phone number verification
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phone Verification</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                position: relative;
                overflow: hidden;
            }

            body::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 50px 50px;
                animation: backgroundMove 20s linear infinite;
            }

            @keyframes backgroundMove {
                0% { transform: translate(0, 0); }
                100% { transform: translate(50px, 50px); }
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                max-width: 420px;
                width: 100%;
                padding: 48px 40px;
                position: relative;
                z-index: 1;
            }

            .header {
                text-align: center;
                margin-bottom: 40px;
            }

            .header .icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                font-size: 2.5rem;
                box-shadow: 0 10px 30px rgba(99, 102, 241, 0.3);
            }

            .header h1 {
                color: #1f2937;
                font-size: 1.875rem;
                font-weight: 700;
                margin-bottom: 8px;
                letter-spacing: -0.025em;
            }

            .header p {
                color: #6b7280;
                font-size: 0.9375rem;
                font-weight: 400;
            }

            .step {
                display: none;
            }

            .step.active {
                display: block;
                animation: fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(12px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .form-group {
                margin-bottom: 24px;
            }

            label {
                display: block;
                color: #374151;
                font-weight: 600;
                margin-bottom: 10px;
                font-size: 0.875rem;
                letter-spacing: 0.01em;
            }

            input[type="tel"] {
                width: 100%;
                padding: 16px 18px;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                font-size: 1rem;
                font-family: 'Inter', sans-serif;
                transition: all 0.2s ease;
                background: white;
            }

            input[type="tel"]:focus {
                outline: none;
                border-color: #6366f1;
                box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
            }

            .channel-select {
                display: flex;
                gap: 12px;
                margin-bottom: 24px;
            }

            .channel-btn {
                flex: 1;
                padding: 14px 20px;
                border: 2px solid #e5e7eb;
                background: white;
                border-radius: 12px;
                cursor: pointer;
                font-weight: 600;
                font-size: 0.9375rem;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                color: #6b7280;
            }

            .channel-btn:hover {
                border-color: #c7d2fe;
                background: #f9fafb;
            }

            .channel-btn.active {
                border-color: #6366f1;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                color: white;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
            }

            .btn {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
            }

            .btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
            }

            .btn:active:not(:disabled) {
                transform: translateY(0);
            }

            .btn:disabled {
                background: #d1d5db;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }

            .message {
                padding: 14px 16px;
                border-radius: 12px;
                margin-bottom: 24px;
                font-size: 0.875rem;
                font-weight: 500;
                display: none;
                border-left: 4px solid;
            }

            .message.show {
                display: block;
                animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            @keyframes slideDown {
                from { opacity: 0; transform: translateY(-8px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .message.error {
                background: #fef2f2;
                color: #dc2626;
                border-color: #dc2626;
            }

            .message.success {
                background: #f0fdf4;
                color: #16a34a;
                border-color: #16a34a;
            }

            .message.info {
                background: #eff6ff;
                color: #2563eb;
                border-color: #2563eb;
            }

            .code-inputs {
                display: flex;
                gap: 12px;
                justify-content: center;
                margin-bottom: 24px;
            }

            .code-input {
                width: 52px;
                height: 60px;
                text-align: center;
                font-size: 1.5rem;
                font-weight: 700;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                transition: all 0.2s ease;
                font-family: 'Inter', monospace;
                background: white;
            }

            .code-input:focus {
                outline: none;
                border-color: #6366f1;
                box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
                transform: scale(1.05);
            }

            .resend-link {
                text-align: center;
                margin-top: 20px;
                color: #6366f1;
                cursor: pointer;
                font-size: 0.875rem;
                font-weight: 600;
                transition: color 0.2s ease;
            }

            .resend-link:hover {
                color: #a855f7;
            }

            .success-icon {
                text-align: center;
                font-size: 5rem;
                margin: 24px 0;
                animation: scaleIn 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            }

            @keyframes scaleIn {
                from { transform: scale(0); opacity: 0; }
                to { transform: scale(1); opacity: 1; }
            }

            .hint {
                text-align: center;
                color: #9ca3af;
                font-size: 0.8125rem;
                margin-top: 12px;
                font-weight: 400;
            }

            .success-content {
                text-align: center;
            }

            .success-content h2 {
                color: #1f2937;
                font-size: 1.5rem;
                font-weight: 700;
                margin-bottom: 12px;
            }

            .success-content p {
                color: #6b7280;
                font-size: 0.9375rem;
                line-height: 1.6;
                margin-bottom: 8px;
            }

            .verified-number {
                display: inline-block;
                background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 700;
            }

            @media (max-width: 480px) {
                .container {
                    padding: 36px 28px;
                }

                .header h1 {
                    font-size: 1.625rem;
                }

                .code-input {
                    width: 46px;
                    height: 54px;
                    font-size: 1.375rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="icon">📱</div>
                <h1>Verify Your Phone</h1>
                <p>Get verified to receive calls from the clinic</p>
            </div>

            <div id="message" class="message"></div>

            <!-- Step 1: Enter Phone Number -->
            <div id="step1" class="step active">
                <div class="form-group">
                    <label for="phoneNumber">Phone Number</label>
                    <input
                        type="tel"
                        id="phoneNumber"
                        placeholder="+49 123 456 7890"
                        autocomplete="tel"
                    >
                    <div class="hint">Enter your number in international format (e.g., +49...)</div>
                </div>

                <div class="form-group">
                    <label>Verification Method</label>
                    <div class="channel-select">
                        <button class="channel-btn active" data-channel="sms">
                            📱 SMS
                        </button>
                        <button class="channel-btn" data-channel="call">
                            📞 Call
                        </button>
                    </div>
                </div>

                <button class="btn" id="sendCodeBtn">Send Verification Code</button>
            </div>

            <!-- Step 2: Enter Verification Code -->
            <div id="step2" class="step">
                <div class="form-group">
                    <label>Enter 6-Digit Code</label>
                    <div class="code-inputs">
                        <input type="text" maxlength="1" class="code-input" data-index="0">
                        <input type="text" maxlength="1" class="code-input" data-index="1">
                        <input type="text" maxlength="1" class="code-input" data-index="2">
                        <input type="text" maxlength="1" class="code-input" data-index="3">
                        <input type="text" maxlength="1" class="code-input" data-index="4">
                        <input type="text" maxlength="1" class="code-input" data-index="5">
                    </div>
                    <div class="hint">Check your <span id="channelText">SMS</span> for the code</div>
                </div>

                <button class="btn" id="verifyCodeBtn">Verify Code</button>
                <div class="resend-link" id="resendLink">← Request New Code</div>
            </div>

            <!-- Step 3: Success -->
            <div id="step3" class="step">
                <div class="success-icon">✅</div>
                <div class="success-content">
                    <h2>Verified!</h2>
                    <p>
                        Your phone number <span class="verified-number" id="verifiedNumber"></span> is now verified with Twilio.
                    </p>
                    <p style="margin-top: 16px;">
                        You can now receive calls from our clinic.
                    </p>
                </div>
            </div>
        </div>

        <script>
            let currentStep = 1;
            let phoneNumber = '';
            let selectedChannel = 'sms';

            // Channel selection
            document.querySelectorAll('.channel-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.channel-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    selectedChannel = btn.dataset.channel;
                });
            });

            // Code input auto-focus
            const codeInputs = document.querySelectorAll('.code-input');
            codeInputs.forEach((input, index) => {
                input.addEventListener('input', (e) => {
                    if (e.target.value.length === 1 && index < codeInputs.length - 1) {
                        codeInputs[index + 1].focus();
                    }
                });

                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Backspace' && !e.target.value && index > 0) {
                        codeInputs[index - 1].focus();
                    }
                });
            });

            // Send verification code
            document.getElementById('sendCodeBtn').addEventListener('click', async () => {
                phoneNumber = document.getElementById('phoneNumber').value.trim();

                if (!phoneNumber) {
                    showMessage('Please enter your phone number', 'error');
                    return;
                }

                if (!phoneNumber.startsWith('+')) {
                    showMessage('Phone number must start with + (international format)', 'error');
                    return;
                }

                const btn = document.getElementById('sendCodeBtn');
                btn.disabled = true;
                btn.textContent = 'Sending...';

                try {
                    const response = await fetch('/api/verify/send', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phone_number: phoneNumber, channel: selectedChannel })
                    });

                    const data = await response.json();

                    if (data.success) {
                        showMessage(data.message, 'success');
                        document.getElementById('channelText').textContent = selectedChannel.toUpperCase();
                        goToStep(2);
                    } else {
                        showMessage(data.message, 'error');
                    }
                } catch (error) {
                    showMessage('Network error. Please try again.', 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Send Verification Code';
                }
            });

            // Verify code
            document.getElementById('verifyCodeBtn').addEventListener('click', async () => {
                const code = Array.from(codeInputs).map(input => input.value).join('');

                if (code.length !== 6) {
                    showMessage('Please enter the complete 6-digit code', 'error');
                    return;
                }

                const btn = document.getElementById('verifyCodeBtn');
                btn.disabled = true;
                btn.textContent = 'Verifying...';

                try {
                    const response = await fetch('/api/verify/check', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phone_number: phoneNumber, code: code })
                    });

                    const data = await response.json();

                    if (data.success) {
                        showMessage(data.message, 'success');
                        document.getElementById('verifiedNumber').textContent = phoneNumber;
                        goToStep(3);
                    } else {
                        showMessage(data.message, 'error');
                        // Clear code inputs on error
                        codeInputs.forEach(input => input.value = '');
                        codeInputs[0].focus();
                    }
                } catch (error) {
                    showMessage('Network error. Please try again.', 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Verify Code';
                }
            });

            // Resend code
            document.getElementById('resendLink').addEventListener('click', () => {
                goToStep(1);
                showMessage('', '');
            });

            // Helper functions
            function goToStep(step) {
                document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
                document.getElementById(`step${step}`).classList.add('active');
                currentStep = step;
            }

            function showMessage(text, type) {
                const msgEl = document.getElementById('message');
                msgEl.textContent = text;
                msgEl.className = 'message';
                if (text) {
                    msgEl.classList.add('show', type);
                }
            }

            // Allow enter key to submit
            document.getElementById('phoneNumber').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') document.getElementById('sendCodeBtn').click();
            });

            codeInputs[5].addEventListener('keypress', (e) => {
                if (e.key === 'Enter') document.getElementById('verifyCodeBtn').click();
            });
        </script>
    </body>
    </html>
    """


async def send_verification_code(request: SendVerificationRequest):
    """
    API endpoint to send verification code via Twilio Verify.

    Args:
        request: Request with phone number and channel

    Returns:
        JSON response with success status
    """
    result = twilio_verify_service.send_verification_code(
        phone_number=request.phone_number,
        channel=request.channel
    )
    return JSONResponse(content=result)


async def verify_code(request: VerifyCodeRequest):
    """
    API endpoint to verify the code entered by user.

    Args:
        request: Request with phone number and code

    Returns:
        JSON response with verification result
    """
    result = twilio_verify_service.verify_code(
        phone_number=request.phone_number,
        code=request.code
    )
    return JSONResponse(content=result)
