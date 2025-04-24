import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

# Rise Up API Configuration
RISEUP_PUBLIC_KEY = os.getenv("RISEUP_PUBLIC_KEY")
RISEUP_PRIVATE_KEY = os.getenv("RISEUP_PRIVATE_KEY")
RISEUP_API_ENDPOINT = os.getenv("RISEUP_API_ENDPOINT")
RISEUP_CREATOR_USER_ID = int(os.getenv("RISEUP_CREATOR_USER_ID", "0")) # Default to 0 if not set

# Learning Box API Configuration
LEARNINGBOX_API_KEY = os.getenv("LEARNINGBOX_API_KEY")
LEARNINGBOX_API_ENDPOINT = os.getenv("LEARNINGBOX_API_ENDPOINT")

# Webhook Configuration
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/learningbox_webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") # Optional secret for signature verification

def get_full_webhook_url():
    if not WEBHOOK_BASE_URL:
        raise ValueError("WEBHOOK_BASE_URL must be set in the .env file")
    return f"{WEBHOOK_BASE_URL.rstrip('/')}{WEBHOOK_PATH}"

# LearningBox SCORM Request Defaults
LB_REQUEST_CLIENT_ID = os.getenv("LB_REQUEST_CLIENT_ID", "001")
LB_REQUEST_TYPE = os.getenv("LB_REQUEST_TYPE", "light")
LB_REQUEST_FORMAT = os.getenv("LB_REQUEST_FORMAT", "scorm2004")
LB_REQUEST_NAVIGATION = os.getenv("LB_REQUEST_NAVIGATION", "free")
LB_REQUEST_WEBHOOK_VERB = os.getenv("LB_REQUEST_WEBHOOK_VERB", "POST")

# Mapping file
MAPPING_FILE_PATH = os.getenv("MAPPING_FILE_PATH", "lb_to_riseup_mapping.json")

# --- Input Validation ---
def validate_config():
    required_vars = [
        ("RISEUP_PUBLIC_KEY", RISEUP_PUBLIC_KEY),
        ("RISEUP_PRIVATE_KEY", RISEUP_PRIVATE_KEY),
        ("RISEUP_API_ENDPOINT", RISEUP_API_ENDPOINT),
        ("RISEUP_CREATOR_USER_ID", RISEUP_CREATOR_USER_ID),
        ("LEARNINGBOX_API_KEY", LEARNINGBOX_API_KEY),
        ("LEARNINGBOX_API_ENDPOINT", LEARNINGBOX_API_ENDPOINT),
        ("WEBHOOK_BASE_URL", WEBHOOK_BASE_URL),
    ]
    missing = [name for name, value in required_vars if not value]
    if missing:
        raise ValueError(f"Missing required configuration variables in .env: {', '.join(missing)}")

    if RISEUP_CREATOR_USER_ID == 0:
         print("Warning: RISEUP_CREATOR_USER_ID is not set or invalid, defaulting to 0.")

    print("Configuration loaded successfully.")

# You can call validate_config() when your scripts start
# if __name__ == "__main__":
#     try:
#         validate_config()
#         print(f"Full Webhook URL: {get_full_webhook_url()}")
#     except ValueError as e:
#         print(f"Configuration Error: {e}") 