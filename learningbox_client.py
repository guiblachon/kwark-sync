import requests
import config
from requests.exceptions import RequestException

class LearningBoxClient:
    def __init__(self):
        self.base_url = config.LEARNINGBOX_API_ENDPOINT.rstrip('/')
        self.api_key = config.LEARNINGBOX_API_KEY
        # Define how the API key is sent. Assuming X-Api-Key header.
        # Change this if Learning Box uses a different method (e.g., Bearer token).
        self.auth_headers = {"X-Gravitee-Api-Key": self.api_key}

    def _make_request(self, method, endpoint, **kwargs):
        """Makes a request to the Learning Box API."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update(self.auth_headers) # Add authentication headers
        headers.setdefault('Accept', 'application/json')
        if method in ('POST', 'PUT') and 'json' in kwargs and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            # Handle potential 204 No Content responses
            if response.status_code == 204:
                return None
            return response.json()
        except RequestException as e:
            print(f"Error during Learning Box API call ({method} {url}): {e}")
            if e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise

    def get_catalog(self):
        """Gets the list of all courses from Learning Box."""
        print("Fetching Learning Box course catalog...")
        response_data = self._make_request('GET', '/learningbox/list')
        if response_data and response_data.get('status') == 'ok':
            courses = response_data.get('modules', [])
            print(f"Successfully fetched {len(courses)} courses from Learning Box.")
            return courses
        else:
            print("Error fetching Learning Box catalog or unexpected status.")
            print(f"Received data: {response_data}")
            return [] # Return empty list on failure

    def request_scorm_export(self, course_id, webhook_url):
        """Requests a SCORM export for a specific course ID."""
        payload = {
            "id": int(course_id), # Ensure ID is an integer
            "client_id": config.LB_REQUEST_CLIENT_ID,
            "type": config.LB_REQUEST_TYPE,
            "format": config.LB_REQUEST_FORMAT,
            "navigation": config.LB_REQUEST_NAVIGATION,
            "webhook_url": webhook_url,
            "webhook_verb": config.LB_REQUEST_WEBHOOK_VERB
        }
        print(f"Requesting SCORM export for Learning Box Course ID: {course_id}")
        try:
            # Assuming the API returns JSON confirmation, adjust if not
            response_data = self._make_request('POST', '/learningbox/request-by-id', json=payload)
            print(f"SCORM export request successful for Course ID {course_id}. Response: {response_data}")
            return response_data # Or True if no specific data is returned on success
        except RequestException as e:
            # Error already logged in _make_request
            print(f"SCORM export request failed for Course ID {course_id}.")
            return None # Indicate failure

# Example usage:
if __name__ == "__main__":
    try:
        config.validate_config()
        client = LearningBoxClient()

        print("\n--- Fetching Catalog ---")
        catalog = client.get_catalog()
        if catalog:
            print(f"First course: {catalog[0]}")
            # Example: Request export for the first course
            first_course_id = catalog[0].get('id')
            if first_course_id:
                print(f"\n--- Requesting SCORM for Course ID: {first_course_id} ---")
                full_webhook_url = config.get_full_webhook_url()
                print(f"Using webhook URL: {full_webhook_url}")
                export_response = client.request_scorm_export(first_course_id, full_webhook_url)
                print(f"Export request response: {export_response}")
        else:
            print("Could not fetch catalog.")

    except ValueError as e:
        print(f"Configuration Error: {e}")
    except RequestException as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 