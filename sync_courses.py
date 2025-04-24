import config
from learningbox_client import LearningBoxClient
from riseup_client import RiseUpClient
import mapping_store
import time
import requests # Added for downloading
import os       # Added for path manipulation
from urllib.parse import urlparse # Added for filename extraction
from requests.exceptions import RequestException

def download_content(url):
    """Downloads content from a URL and returns bytes and filename."""
    if not url:
        return None, None
    try:
        print(f"    Downloading content from: {url}", flush=True)
        response = requests.get(url, stream=True, timeout=30) # Added timeout
        response.raise_for_status()

        # Extract filename from URL path
        path = urlparse(url).path
        filename = os.path.basename(path) if path else "downloaded_file"
        # Improve filename if it's empty or just '/' e.g. from base URLs
        if not filename or filename == "/":
             filename = url.split('/')[-1] or "downloaded_file"
             # Add extension based on content type if possible?
             content_type = response.headers.get('content-type')
             if content_type:
                 # Basic extension mapping
                 if 'image/jpeg' in content_type and not filename.lower().endswith(('.jpg', '.jpeg')):
                     filename += ".jpg"
                 elif 'image/png' in content_type and not filename.lower().endswith('.png'):
                      filename += ".png"
                 elif 'image/gif' in content_type and not filename.lower().endswith('.gif'):
                      filename += ".gif"
                 # Add more types if needed

        content = response.content
        print(f"    Downloaded {len(content)} bytes as '{filename}'", flush=True)
        return content, filename
    except RequestException as e:
        print(f"    Warning: Failed to download content from {url}: {e}", flush=True)
        return None, None
    except Exception as e:
        print(f"    Warning: Unexpected error downloading {url}: {e}", flush=True)
        return None, None

def sync_course_structure(lb_course, riseup_client):
    """Creates the Course, Module, and SCORM Step structure in Rise Up."""
    lb_id = lb_course.get('id')
    lb_title = lb_course.get('name', f"LearningBox Course {lb_id}")
    lb_desc = lb_course.get('description', '')
    lb_short_desc = lb_course.get('short_description', '') # Use as objective?
    lb_duration = lb_course.get('duration', 0) # Duration is in minutes for RiseUp
    lb_reference = lb_course.get('code', f"LB_{lb_id}")
    # Get image/banner URLs
    lb_image_url = lb_course.get('image')
    lb_banner_url = lb_course.get('banner')
    # Extract tag names for keywords
    lb_tags = lb_course.get('tags', [])
    lb_keywords = [tag.get('name') for tag in lb_tags if tag.get('name')]

    print(f"\nProcessing LearningBox Course: {lb_title} (ID: {lb_id})", flush=True)
    if lb_keywords:
        print(f"  Found tags to use as keywords: {lb_keywords}", flush=True)

    try:
        # 1. Create Rise Up Course
        riseup_course = riseup_client.create_course(
            title=lb_title,
            description=lb_desc,
            objective=lb_short_desc,
            reference=lb_reference,
            eduduration=lb_duration,
            language="fr-FR",
            keywords=lb_keywords # Pass keywords here
        )
        if not riseup_course or 'id' not in riseup_course:
            print(f"Failed to create RiseUp Course for LB ID {lb_id}. Skipping.")
            return None
        riseup_course_id = riseup_course['id']
        print(f"  Created RiseUp Course ID: {riseup_course_id}")

        # --- Upload Image and Banner --- #
        image_content, image_filename = download_content(lb_image_url)
        if image_content and image_filename:
            try:
                print(f"  Attempting to upload image: {image_filename}")
                riseup_client.upload_course_image(riseup_course_id, image_content, image_filename)
            except (RequestException, ConnectionError) as e:
                print(f"  Warning: Failed to upload image for Course ID {riseup_course_id}: {e}")
            except Exception as e:
                 print(f"  Warning: Unexpected error uploading image for Course ID {riseup_course_id}: {e}")

        banner_content, banner_filename = download_content(lb_banner_url)
        if banner_content and banner_filename:
            try:
                print(f"  Attempting to upload banner: {banner_filename}")
                riseup_client.upload_course_banner(riseup_course_id, banner_content, banner_filename)
            except (RequestException, ConnectionError) as e:
                print(f"  Warning: Failed to upload banner for Course ID {riseup_course_id}: {e}")
            except Exception as e:
                 print(f"  Warning: Unexpected error uploading banner for Course ID {riseup_course_id}: {e}")
        # --- End Upload --- #

        # 2. Create Rise Up Module
        module_title = f"Module 1"
        riseup_module = riseup_client.create_module(
            course_id=riseup_course_id,
            title=module_title,
            reference=f"{lb_reference}_M1",
            eduduration=lb_duration # Pass the duration here
        )
        if not riseup_module or 'id' not in riseup_module:
            print(f"Failed to create RiseUp Module for LB ID {lb_id}. Skipping.")
            return None
        riseup_module_id = riseup_module['id']
        print(f"  Created RiseUp Module ID: {riseup_module_id}")

        # 3. Create Rise Up SCORM Step
        step_title = f"Contenu"
        riseup_step = riseup_client.create_scorm_step(
            module_id=riseup_module_id,
            title=step_title,
            reference=f"{lb_reference}_M1_S1"
        )
        if not riseup_step or 'id' not in riseup_step:
            print(f"Failed to create RiseUp Step for LB ID {lb_id}. Skipping.")
            return None
        riseup_step_id = riseup_step['id']
        print(f"  Created RiseUp Step ID: {riseup_step_id}")

        return riseup_step_id # Return the crucial step ID for mapping

    except (RequestException, ConnectionError) as e:
        print(f"API Error processing LB Course ID {lb_id}: {e}. Skipping.", flush=True)
        return None
    except Exception as e:
        print(f"Unexpected error processing LB Course ID {lb_id}: {e}. Skipping.", flush=True)
        return None

def main():
    print("Starting LearningBox to Rise Up Sync Process...")
    try:
        config.validate_config()
        lb_client = LearningBoxClient()
        riseup_client = RiseUpClient()
        webhook_url = config.get_full_webhook_url()
        print(f"Using Webhook URL: {webhook_url}")
    except (ValueError, RequestException, ConnectionError) as e:
        print(f"Initialization Error: {e}")
        return

    # Load existing mapping to potentially skip already processed courses
    # or re-request SCORM if needed (logic TBD based on requirements)
    existing_mapping = mapping_store.load_mapping()
    print(f"Loaded {len(existing_mapping)} existing mappings.")

    lb_catalog = lb_client.get_catalog()
    if not lb_catalog:
        print("No courses found in Learning Box catalog or failed to fetch. Exiting.")
        return

    print(f"Found {len(lb_catalog)} courses in Learning Box catalog.")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for lb_course in lb_catalog:
        lb_id = lb_course.get('id')
        if not lb_id:
            print(f"Skipping course due to missing ID: {lb_course.get('name', '[No Name]')}")
            fail_count += 1
            continue

        # --- Check if already mapped --- #
        # Basic check: skip if mapping exists. Add more complex logic if needed
        # (e.g., check modification dates, allow force refresh).
        if str(lb_id) in existing_mapping:
            print(f"Skipping LB Course ID {lb_id} ('{lb_course.get('name')}') - already mapped.")
            skip_count += 1
            continue # Skip to the next course
        # --- End Check --- #

        # Create RiseUp Structure
        riseup_step_id = sync_course_structure(lb_course, riseup_client)

        if riseup_step_id:
            # Store the mapping
            mapping_store.add_or_update_mapping(lb_id, riseup_step_id)

            # Request SCORM Export
            export_result = lb_client.request_scorm_export(lb_id, webhook_url)
            if export_result is not None: # Assuming None indicates failure
                print(f"  Successfully requested SCORM export for LB ID {lb_id}. Waiting for webhook.")
                success_count += 1
            else:
                print(f"  Failed to request SCORM export for LB ID {lb_id}. Mapping was saved, but check LearningBox.")
                fail_count += 1
                # Consider cleanup or retry logic here?
        else:
            print(f"Failed to create RiseUp structure for LB ID {lb_id}. See previous errors.")
            fail_count += 1

        # Optional: Add delay between requests to respect API rate limits if necessary
        # time.sleep(1) # e.g., sleep 1 second

    print("\n--- Sync Process Complete ---")
    print(f"Successfully processed (structure created & SCORM requested): {success_count}")
    print(f"Skipped (already mapped): {skip_count}")
    print(f"Failed: {fail_count}")
    print("Ensure the webhook handler is running to receive and upload SCORM packages.")

if __name__ == "__main__":
    main() 