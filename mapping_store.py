import json
import os
import config

def load_mapping():
    """Loads the mapping from the JSON file specified in config."""
    if not os.path.exists(config.MAPPING_FILE_PATH):
        return {}
    try:
        with open(config.MAPPING_FILE_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Mapping file {config.MAPPING_FILE_PATH} is corrupted. Starting with an empty mapping.")
        return {}
    except IOError as e:
        print(f"Warning: Could not read mapping file {config.MAPPING_FILE_PATH}: {e}. Starting with an empty mapping.")
        return {}

def save_mapping(mapping_data):
    """Saves the mapping data to the JSON file specified in config."""
    try:
        with open(config.MAPPING_FILE_PATH, 'w') as f:
            json.dump(mapping_data, f, indent=4)
    except IOError as e:
        print(f"Error: Could not write mapping file {config.MAPPING_FILE_PATH}: {e}")

def add_or_update_mapping(lb_course_id, riseup_step_id):
    """Adds or updates a mapping for a specific Learning Box course ID."""
    mapping = load_mapping()
    mapping[str(lb_course_id)] = riseup_step_id # Ensure keys are strings
    save_mapping(mapping)
    print(f"Mapping updated: LB Course {lb_course_id} -> RiseUp Step {riseup_step_id}")

def get_riseup_step_id(lb_course_id):
    """Retrieves the Rise Up Step ID for a given Learning Box course ID."""
    mapping = load_mapping()
    return mapping.get(str(lb_course_id)) # Ensure lookup key is a string

if __name__ == '__main__':
    # Example Usage
    print("Loading initial mapping:")
    print(load_mapping())

    print("\nAdding/Updating mappings:")
    add_or_update_mapping(123, 987)
    add_or_update_mapping('456', 654)
    add_or_update_mapping(123, 999) # Update existing

    print("\nLoading final mapping:")
    final_mapping = load_mapping()
    print(final_mapping)

    print("\nRetrieving specific mappings:")
    print(f"RiseUp Step ID for LB 123: {get_riseup_step_id(123)}")
    print(f"RiseUp Step ID for LB '456': {get_riseup_step_id('456')}")
    print(f"RiseUp Step ID for LB 789: {get_riseup_step_id(789)}") 