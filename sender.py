import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from a .env file for local development
load_dotenv()

# --- Configuration from Environment Variables ---
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

# The URL of your deployed tracking server API
TRACKING_API_URL = os.environ.get("TRACKING_SERVER_URL")

def send_tracked_email(recipient_email, subject, body_html):
    """
    Registers an email with the tracking server and sends it.
    """
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, TRACKING_API_URL]):
        print("Error: SMTP or TRACKING_SERVER_URL environment variables not set.")
        return

    # 1. Register the email with our tracking server to get a tracking URL
    register_endpoint = f"{TRACKING_API_URL}/register"
    try:
        response = requests.post(register_endpoint, json={
            "recipient": recipient_email,
            "subject": subject
        })
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        tracking_data = response.json()
        tracking_pixel_url = tracking_data['tracking_url']
        print(f"Successfully registered email. Tracking URL: {tracking_pixel_url}")
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not register email with tracking server: {e}")
        return

    # 2. Create the tracking pixel HTML and add it to the email body
    tracking_pixel_html = f'<img src="{tracking_pixel_url}" width="1" height="1" alt="" border="0" style="display:none;"/>'
    full_html = body_html + tracking_pixel_html

    # 3. Construct and send the email message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = recipient_email
    msg.attach(MIMEText(full_html, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, msg.as_string())
            print(f"Successfully sent tracked email to {recipient_email}")
    except smtplib.SMTPException as e:
        print(f"Error sending email via SMTP: {e}")

if __name__ == '__main__':
    # --- Example Usage ---
    recipient = "imanistewart@gmail.com" # CHANGE THIS
    email_subject = "A Tracked Message from the Cloud!"
    email_body = """
    <h1>Hello from a deployed tracking service!</h1>
    <p>This email's 'open' event is being tracked by a server hosted on the web.</p>
    """

    if recipient == "recipient_email@example.com":
        print("!!! PLEASE CHANGE THE 'recipient' VARIABLE IN sender.py BEFORE RUNNING !!!")
    else:
        send_tracked_email(recipient, email_subject, email_body)