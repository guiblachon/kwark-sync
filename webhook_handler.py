from flask import Flask, request, jsonify, abort
import config
import base64
import mapping_store
from riseup_client import RiseUpClient
from urllib.parse import parse_qs
import io
from requests.exceptions import RequestException

app = Flask(__name__)

# Initialize RiseUp Client (consider if it needs token refresh logic within request scope)
# For simplicity, assuming the client handles token refresh internally as needed.
try:
    config.validate_config() # Ensure config is valid at startup
    riseup_client = RiseUpClient()
except ValueError as e:
    # Log error and potentially prevent app start if config is invalid
    app.logger.error(f"Webhook Handler Configuration Error: {e}")
    # Depending on deployment, you might raise the error here
    # raise
    riseup_client = None # Ensure client is None if config fails

@app.route(config.WEBHOOK_PATH, methods=['POST'])
def handle_learningbox_webhook():
    if not riseup_client:
        app.logger.error("Webhook received but RiseUp client is not configured.")
        return jsonify({"status": "error", "message": "Server configuration error"}), 500

    app.logger.info(f"Webhook received at {config.WEBHOOK_PATH}")

    # Optional: Add signature verification if Learning Box supports it
    # using config.WEBHOOK_SECRET

    if request.content_type != 'application/x-www-form-urlencoded':
        app.logger.warning(f"Received webhook with unexpected Content-Type: {request.content_type}")
        # Depending on LB behavior, you might still try to parse or abort
        # abort(415, description="Unsupported Media Type: Expected application/x-www-form-urlencoded")

    try:
        # Raw data is bytes, decode it assuming UTF-8 (common for urlencoded)
        raw_data = request.get_data(as_text=True)
        app.logger.debug(f"Raw webhook data: {raw_data[:500]}...") # Log snippet
        parsed_data = parse_qs(raw_data)
        app.logger.info(f"Parsed webhook data keys: {list(parsed_data.keys())}")

        # Extract data based on the example format: modules[0][id] and modules[0][zip]
        lb_course_id_list = parsed_data.get('modules[0][id]')
        scorm_zip_b64_list = parsed_data.get('modules[0][zip]')

        if not lb_course_id_list or not scorm_zip_b64_list:
            app.logger.error(f"Missing 'modules[0][id]' or 'modules[0][zip]' in webhook data: {parsed_data}")
            return jsonify({"status": "error", "message": "Missing required data fields"}), 400

        # parse_qs returns lists, get the first element
        lb_course_id = lb_course_id_list[0]
        scorm_zip_b64 = scorm_zip_b64_list[0]

        app.logger.info(f"Processing webhook for Learning Box Course ID: {lb_course_id}")

        # 1. Find the corresponding RiseUp Step ID
        riseup_step_id = mapping_store.get_riseup_step_id(lb_course_id)
        if not riseup_step_id:
            app.logger.error(f"No RiseUp Step ID found in mapping for LB Course ID: {lb_course_id}")
            # Return 2xx to acknowledge receipt but log error, LB might not retry on 4xx/5xx
            return jsonify({"status": "acknowledged_error", "message": "Mapping not found"}), 200

        app.logger.info(f"Found corresponding RiseUp Step ID: {riseup_step_id}")

        # 2. Decode the Base64 SCORM data
        try:
            scorm_zip_bytes = base64.b64decode(scorm_zip_b64)
            app.logger.info(f"Successfully decoded Base64 SCORM data ({len(scorm_zip_bytes)} bytes).")
        except base64.binascii.Error as e:
            app.logger.error(f"Failed to decode Base64 SCORM data for LB Course ID {lb_course_id}: {e}")
            return jsonify({"status": "error", "message": "Invalid Base64 data"}), 400

        # 3. Upload to Rise Up
        try:
            filename = f"lb_{lb_course_id}_scorm.zip"
            # Use io.BytesIO to treat bytes as a file-like object for requests
            scorm_file_like = io.BytesIO(scorm_zip_bytes)

            upload_response = riseup_client.upload_scorm_content(riseup_step_id, scorm_file_like, filename)
            app.logger.info(f"Successfully uploaded SCORM to RiseUp Step ID {riseup_step_id}. Response: {upload_response}")
            return jsonify({"status": "success", "message": "SCORM uploaded to RiseUp"}), 200
        except (RequestException, ConnectionError) as e:
            app.logger.error(f"Failed to upload SCORM to RiseUp Step ID {riseup_step_id}: {e}")
            # Return 5xx to indicate server-side issue during upload, LB might retry
            return jsonify({"status": "error", "message": "Failed to upload SCORM to RiseUp"}), 502 # Bad Gateway might be appropriate

    except Exception as e:
        app.logger.exception(f"An unexpected error occurred processing webhook: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    # Note: Use a proper WSGI server like Gunicorn or Waitress for production
    # Development server usage: flask --app webhook_handler run
    # Set host='0.0.0.0' to be accessible externally (e.g., for ngrok)
    app.run(debug=True, host='0.0.0.0', port=5001) # Use a port other than default 5000 if needed 