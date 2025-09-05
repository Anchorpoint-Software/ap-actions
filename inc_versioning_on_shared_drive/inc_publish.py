import apsync as aps
import uuid
from datetime import datetime
import os
import json
import anchorpoint as ap
import re


def get_master_filename(path, appendix):
    """
    Given a file path and an appendix, return the master filename by removing initials and increments.
    Example:
        P25123-LIN_US_Autum_Toolkit_mn_v002.c4d -> P25123-LIN_US_Autum_Toolkit_master.c4d
    """
    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)
    # Remove initials and increments: match _[a-zA-Z]+_v[0-9]+$ or _v[0-9]+$ at the end
    # Also handle _v0002, _v02, _mn_v002, etc.
    # Remove trailing _[a-zA-Z]+_v\d+ or _v\d+
    new_name = re.sub(r'(_[a-zA-Z]+)?_v\d+$', '', name)
    master_name = f"{new_name}_{appendix}{ext}"
    return master_name


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
        master_filename = get_master_filename(path, appendix)
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
