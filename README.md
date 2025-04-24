# LearningBox to Rise Up SCORM Sync

This project contains Python scripts to synchronize course structures from Learning Box to Rise Up and handle SCORM package uploads via a webhook.

## Features

*   **`sync_courses.py`**: 
    *   Fetches the course catalog from Learning Box.
    *   For each Learning Box course:
        *   Creates a corresponding Course in Rise Up.
        *   Creates a single Module within the Rise Up Course.
        *   Creates a single SCORM Step within the Rise Up Module.
        *   Requests a SCORM package export from Learning Box, providing a webhook URL for notification.
        *   Stores a mapping between the Learning Box Course ID and the created Rise Up SCORM Step ID.
*   **`webhook_handler.py`**: 
    *   Acts as a webhook receiver (using Flask).
    *   Listens for POST requests from Learning Box containing the generated SCORM package.
    *   Parses the request to get the Learning Box Course ID and the Base64 encoded SCORM zip data.
    *   Looks up the corresponding Rise Up Step ID using the mapping.
    *   Decodes the Base64 data.
    *   Uploads the SCORM zip file to the correct Rise Up Step.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```
2.  **Create a virtual environment (optional but recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables:**
    *   Copy `.env.example` to `.env`.
    *   Fill in your API keys, endpoints, and the base URL for your webhook receiver in the `.env` file.
    *   Ensure your webhook receiver URL (`WEBHOOK_BASE_URL` + `WEBHOOK_PATH`) is publicly accessible by Learning Box (e.g., using ngrok for local development or deploying the webhook handler).

## Usage

1.  **Run the synchronization script:**
    ```bash
    python sync_courses.py
    ```
    This will create the structures in Rise Up and trigger SCORM exports from Learning Box.

2.  **Run the webhook handler:**
    ```bash
    flask --app webhook_handler run
    ```
    (Or use a production server like Gunicorn: `gunicorn -w 4 'webhook_handler:app'`)
    Keep this running to receive notifications and upload SCORM packages as they become available.

## Configuration

All configuration is managed via the `.env` file. See `.env.example` for details.

## Modules

*   `config.py`: Loads and validates configuration from `.env`.
*   `riseup_client.py`: Client library for Rise Up API interactions.
*   `learningbox_client.py`: Client library for Learning Box API interactions.
*   `sync_courses.py`: Main synchronization script.
*   `webhook_handler.py`: Flask application for webhook receiving.
*   `mapping_store.py`: Utility to manage the ID mapping between systems. 