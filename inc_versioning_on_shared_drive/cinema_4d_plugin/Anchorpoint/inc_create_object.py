import apsync as aps
import anchorpoint as ap
import sys
import json
import os
from datetime import datetime
import uuid

# Summary
# This script is called by the Anchorpoint plugin for Cinema 4D to publish a file.
# It takes a look at the file path and the message provided by the the cinema 4D plugin,
# and creates a new timeline entry using the shared settings of the workspace and project.
# It also creates a master file by copying the published file and appending "_master" to the filename.

# This function is called form the C4D plugin


def main():
    arguments = sys.argv[1]
    arguments = arguments.replace("\\", "\\\\")
    msg = ""
    path = ""
    ctx = ap.get_context()

    # load the existing history from shared settings
    project_settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings")
    workspace_settings = aps.SharedSettings(
        ctx.workspace_id, "inc_workspace_settings")
    history_array = project_settings.get("inc_versions", [])

    # Default appendix for the master file
    appendix = "master"

    # Parse the JSON string
    try:
        parsed_arguments = json.loads(arguments)
        # raise Exception("The output could not be read")
        # Access and print the "msg" object
        if "msg" in parsed_arguments:
            msg = parsed_arguments["msg"]
        if "path" in parsed_arguments:
            path = parsed_arguments["path"]
        else:
            raise Exception("The output could not be read")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON.")

    # Set the file status to Modified
    file_status = "Modified"
    # Create a random id
    version_id = uuid.uuid4().hex[:8]

    # Build the json object that will be stored in the shared settings
    json_object = {
        "user_email": ctx.email,
        "message": msg,
        "time": str(datetime.now()),
        "id": version_id,
        "type": "cinema4d",
        "files": [
            {"path": path,
             "status": file_status}
        ]
    }

    # Add the new entry to the history and store it
    json_object_str = json.dumps(json_object)
    history_array.append(json_object_str)
    project_settings.set("inc_versions", history_array)
    project_settings.store()

    # Set some attributes on the master file
    database = ap.get_api()

    # Update the master file
    project_base_name = os.path.basename(ctx.project_path)
    master_filename = f"{project_base_name}_{appendix}.c4d"
    master_path = os.path.join(os.path.dirname(path), master_filename)
    aps.copy_file(path, master_path, True)

    file_base_name = os.path.basename(path).split(".")[0]

    # Set the source file name (the one with the increment)
    database.attributes.set_attribute_value(
        master_path, "Source File", file_base_name)

    # Mark it as a master with a tag for better visibility
    tag = aps.AttributeTag("master", "yellow")
    database.attributes.set_attribute_value(master_path, "Type", tag)

    # Trigger webhook if set
    webhook_url = workspace_settings.get("webhook_url", "")
    if webhook_url:
        try:
            import requests

            project = aps.get_project(path)

            payload = {
                "project_name": project.name,
                # an app link to the anchorpoint timeline
                "project_app_link": f"https://anchorpoint.app/link?p=projects%2F{project.id}%2F%3FswTime%3D",
                "user_email": ctx.email,
                "message": msg,
                "time": str(datetime.now()),
                "id": version_id,
                "type": "cinema4d",
                "files": [
                    {"path": path,
                     "status": file_status},
                ]
            }

            requests.post(webhook_url, json=payload)
        except Exception as e:
            raise Exception(f"Failed to send webhook: {e}")

    # Print a success to stdout so the C4D plugin can read it
    sys.__stdout__.write("The file has been published")


if __name__ == "__main__":
    main()
