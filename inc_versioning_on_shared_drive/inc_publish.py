import apsync as aps
import anchorpoint as ap
import json
import os
from datetime import datetime
import uuid


def publish_file(msg, path, type):

    ctx = ap.get_context()

    # load the existing history from shared settings
    project_settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings")
    workspace_settings = aps.SharedSettings(
        ctx.workspace_id, "inc_workspace_settings")
    history_array = project_settings.get("inc_versions", [])

    # Check if we need to create a master file
    create_master = project_settings.get("create_master_file", True)

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
        "type": type,
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

    if create_master:
        # Set some attributes on the master file
        database = ap.get_api()
        appendix = project_settings.get("master_file_appendix", "master")
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

    return True
