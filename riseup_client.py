import requests
import base64
import time
import config
from requests.exceptions import RequestException

class RiseUpClient:
    def __init__(self):
        self.base_url = config.RISEUP_API_ENDPOINT.rstrip('/')
        self.public_key = config.RISEUP_PUBLIC_KEY
        self.private_key = config.RISEUP_PRIVATE_KEY
        self.creator_user_id = config.RISEUP_CREATOR_USER_ID
        self.access_token = None
        self.token_expiry = 0

    def _get_auth_header(self):
        """Gets the Basic Auth header for token requests."""
        credentials = f"{self.public_key}:{self.private_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    def _ensure_token(self):
        """Ensures a valid access token is available, refreshing if necessary."""
        if not self.access_token or time.time() >= self.token_expiry:
            print("RiseUp token expired or not found, requesting new token...")
            token_url = f"{self.base_url}/oauth/token"
            headers = {
                "Authorization": self._get_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"grant_type": "client_credentials"}
            try:
                response = requests.post(token_url, headers=headers, data=data)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Set expiry a bit earlier to avoid edge cases
                self.token_expiry = time.time() + token_data['expires_in'] - 60
                print("RiseUp token obtained successfully.")
            except RequestException as e:
                print(f"Error obtaining RiseUp token: {e}")
                if e.response is not None:
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response body: {e.response.text}")
                self.access_token = None
                self.token_expiry = 0
                raise # Re-raise the exception after logging

    def _make_request(self, method, endpoint, **kwargs):
        """Makes an authenticated request to the RiseUp API."""
        self._ensure_token()
        if not self.access_token:
            raise ConnectionError("Failed to obtain RiseUp access token.")

        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"
        headers.setdefault('Accept', 'application/json')
        if method in ('POST', 'PUT') and 'json' in kwargs and 'Content-Type' not in headers:
             headers['Content-Type'] = 'application/json'

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()

            # Handle potential 204 No Content responses
            if response.status_code == 204:
                return None
            # Handle 206 Partial Content (though we might need specific logic later if needed)
            if response.status_code == 206:
                print(f"Warning: Received 206 Partial Content for {url}. Full handling may be needed.")
                # Potentially parse Link/Content-Range headers here if pagination is required
            return response.json()
        except RequestException as e:
            print(f"Error during RiseUp API call ({method} {url}): {e}")
            if e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise

    def create_course(self, title, description="", objective="", reference="", eduduration=0, language="en-US", keywords=None, **other_fields):
        """Creates a new course in Rise Up."""
        payload = {
            "title": title,
            "type": "internal", # As per requirement
            "iduser": self.creator_user_id,
            "language": language,
            "description": description,
            "objective": objective,
            "reference": reference,
            "eduduration": eduduration,
            "state": "validated", # Or "draft"?
            "visible": True, # Default visibility
            # Only include keywords if provided and it's a non-empty list
            # RiseUp API expects an array, even if empty, if the key is present
            "keywords": keywords if keywords is not None else [],
            **other_fields
        }
        # Remove keywords key if the list is empty and RiseUp API doesn't like empty lists
        # if not payload["keywords"]:
        #     del payload["keywords"]

        print(f"Creating RiseUp Course: {title}")
        return self._make_request('POST', '/courses', json=payload)

    def create_module(self, course_id, title, description="", reference="", position=1, eduduration=0):
        """Creates a new module within a course."""
        payload = {
            "idtraining": course_id,
            "title": title,
            "type": "online", # For SCORM
            "description": description,
            "reference": reference,
            "position": position,
            "eduduration": eduduration # Add duration to payload
        }
        print(f"Creating RiseUp Module '{title}' in Course ID {course_id} with duration {eduduration}")
        return self._make_request('POST', '/modules', json=payload)

    def create_scorm_step(self, module_id, title, description="", reference="", position=1):
        """Creates a new SCORM step within a module."""
        payload = {
            "idmodule": module_id,
            "title": title,
            "type": "scorm",
            "description": description,
            "reference": reference,
            "position": position
        }
        print(f"Creating RiseUp SCORM Step '{title}' in Module ID {module_id}")
        return self._make_request('POST', '/steps', json=payload)

    def upload_scorm_content(self, step_id, file_content, filename="scorm_package.zip"):
        """Uploads SCORM content to a specific step."""
        endpoint = f"/steps/content/{step_id}"
        files = {
            'file': (filename, file_content, 'application/zip')
        }
        # Note: requests handles multipart/form-data encoding automatically when using 'files'
        # We don't set Content-Type explicitly here for multipart
        print(f"Uploading SCORM content to Step ID {step_id}")
        # Need to pass headers without Content-Type for multipart
        self._ensure_token()
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        try:
            response = requests.post(f"{self.base_url}{endpoint}", headers=headers, files=files)
            response.raise_for_status()
            print(f"SCORM upload successful for Step ID {step_id}")
            if response.status_code == 204:
                return None
            return response.json() # Return response data if any (e.g., updated step info)
        except RequestException as e:
             print(f"Error uploading SCORM to RiseUp Step {step_id}: {e}")
             if e.response is not None:
                 print(f"Response status: {e.response.status_code}")
                 print(f"Response body: {e.response.text}")
             raise

    # Optional: Add methods for image/banner upload if needed later
    def upload_course_image(self, course_id, image_content, filename):
         """Uploads an image for a course."""
         endpoint = f"/courses/image/{course_id}"
         files = {
             'file': (filename, image_content)
         }
         print(f"Uploading image '{filename}' to Course ID {course_id}")
         # Use _make_request but with files, Content-Type will be set by requests
         # Need to adjust _make_request or handle headers specifically for multipart
         self._ensure_token()
         headers = {
             'Authorization': f"Bearer {self.access_token}",
             'Accept': 'application/json'
         }
         try:
             response = requests.post(f"{self.base_url}{endpoint}", headers=headers, files=files)
             response.raise_for_status()
             print(f"Image upload successful for Course ID {course_id}")
             if response.status_code == 204:
                 return None
             return response.json()
         except RequestException as e:
             print(f"Error uploading image to RiseUp Course {course_id}: {e}")
             if e.response is not None:
                 print(f"Response status: {e.response.status_code}")
                 print(f"Response body: {e.response.text}")
             raise

    def upload_course_banner(self, course_id, banner_content, filename):
        """Uploads a banner for a course."""
        endpoint = f"/courses/banner/{course_id}" # Corrected endpoint
        files = {
            'file': (filename, banner_content)
        }
        print(f"Uploading banner '{filename}' to Course ID {course_id}")
        self._ensure_token()
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Accept': 'application/json'
        }
        try:
            response = requests.post(f"{self.base_url}{endpoint}", headers=headers, files=files)
            response.raise_for_status()
            print(f"Banner upload successful for Course ID {course_id}")
            if response.status_code == 204:
                return None
            return response.json()
        except RequestException as e:
            print(f"Error uploading banner to RiseUp Course {course_id}: {e}")
            if e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise

# Example usage:
if __name__ == "__main__":
    try:
        config.validate_config()
        client = RiseUpClient()
        # Example: Create a course (ensure config is set up)
        # course_data = client.create_course(
        #     title="API Test Course",
        #     description="This is a test course created via API.",
        #     reference="API_TEST_001",
        #     eduduration=60
        # )
        # print("Course created:", course_data)

        # if course_data and course_data.get('id'):
        #     course_id = course_data['id']
        #     module_data = client.create_module(course_id, "Test Module 1")
        #     print("Module created:", module_data)

        #     if module_data and module_data.get('id'):
        #         module_id = module_data['id']
        #         step_data = client.create_scorm_step(module_id, "Test SCORM Step 1")
        #         print("Step created:", step_data)

        #         # Example Upload (replace with actual file reading and step_id)
        #         # step_id_to_upload = step_data['id']
        #         # try:
        #         #     with open("path/to/your/scorm.zip", "rb") as f:
        #         #         scorm_content = f.read()
        #         #     upload_response = client.upload_scorm_content(step_id_to_upload, scorm_content, "scorm.zip")
        #         #     print("Upload response:", upload_response)
        #         # except FileNotFoundError:
        #         #     print("SCORM file not found for upload example.")

        print("RiseUp client initialized. Ready for operations.")

    except ValueError as e:
        print(f"Configuration Error: {e}")
    except (RequestException, ConnectionError) as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 