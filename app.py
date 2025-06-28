import os
import uuid
import logging
from flask import Flask, request, send_file, jsonify
from flask import render_template
import io
from database import get_db_connection, log_open_event

# --- Basic Setup ---
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Create a 1x1 transparent GIF pixel in memory on startup ---
PIXEL_BYTES = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
PIXEL_BUFFER = io.BytesIO(PIXEL_BYTES)

# --- API Routes ---

@app.route('/')
def home():
    return "Email Tracking Server is running."

@app.route('/dashboard')
def dashboard():
    """Displays a dashboard of tracked emails and their open events."""
    conn = get_db_connection()
    
    # Query to get all emails and their associated open events
    query = """
    SELECT
        t.tracking_id, t.recipient, t.subject, t.sent_at,
        o.opened_at, o.ip_address
    FROM tracked_emails t
    LEFT JOIN open_events o ON t.tracking_id = o.tracking_id
    ORDER BY t.sent_at DESC, o.opened_at ASC;
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    # Process the data to group open events by email
    emails = {}
    for row in rows:
        tid = row['tracking_id']
        if tid not in emails:
            emails[tid] = {
                'recipient': row['recipient'],
                'subject': row['subject'],
                'sent_at': row['sent_at'],
                'open_events': []
            }
        if row['opened_at']:
            emails[tid]['open_events'].append({'opened_at': row['opened_at'], 'ip_address': row['ip_address']})

    return render_template('dashboard.html', emails=emails.values())

@app.route('/register', methods=['POST'])
def register_email():
    """
    Endpoint for the sender script to register an email before sending.
    Returns a unique tracking ID and the full tracking URL.
    """
    data = request.get_json()
    if not data or 'recipient' not in data or 'subject' not in data:
        return jsonify({"error": "Missing recipient or subject"}), 400

    tracking_id = str(uuid.uuid4())
    recipient = data['recipient']
    subject = data['subject']

    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tracked_emails (tracking_id, recipient, subject) VALUES (?, ?, ?)",
            (tracking_id, recipient, subject)
        )
        conn.commit()
        conn.close()
        logging.info(f"Registered email for {recipient} with ID: {tracking_id}")

        # The base URL should be configured for your deployment environment
        base_url = os.environ.get('TRACKING_SERVER_URL', request.host_url.rstrip('/'))
        tracking_url = f"{base_url}/track/{tracking_id}"

        return jsonify({
            "tracking_id": tracking_id,
            "tracking_url": tracking_url
        }), 201
    except Exception as e:
        logging.error(f"Database error on registration: {e}")
        return jsonify({"error": "Could not register email"}), 500


@app.route('/track/<tracking_id>')
def track_open(tracking_id):
    """
    This is the tracking endpoint. It gets hit when the email is opened.
    """
    try:
        # Log the open event
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        log_open_event(tracking_id, ip_address, user_agent)
        logging.info(f"PIXEL_ACCESS: Tracking ID {tracking_id} from IP {ip_address}")

    except Exception as e:
        # Fail silently to ensure the pixel is always served
        logging.error(f"Error logging open for {tracking_id}: {e}")

    # Always serve the 1x1 transparent pixel
    return send_file(
        PIXEL_BUFFER,
        mimetype='image/gif',
        # Tell clients and proxies not to cache the pixel
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0'}
    )

if __name__ == '__main__':
    # This block is for local development only.
    # For production, use a WSGI server like Gunicorn.
    from database import init_db
    init_db() # Ensure DB is created when running locally
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)