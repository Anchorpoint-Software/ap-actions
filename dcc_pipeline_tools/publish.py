from typing import cast
import apsync as aps
import uuid
from datetime import datetime
import os
import json
import anchorpoint as ap
from PIL import Image


def get_master_filename(path, appendix):
    """
    Given a file path and an appendix, return the master filename by removing initials and increments.
    Examples:
        C4324-EN_Autum_Toolkit_mn_v002.c4d -> C4324-EN_Autum_Toolkit_master.c4d
        bla_v001.c4d -> bla_master.c4d
        bla.001.c4d -> bla_master.c4d
        object_mn_0002.c4d -> object_mn_master.c4d
    """
    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)

    new_name = name
    sepparator = ""

    # Case 1: filenames like bla_v001 or bla_mn_v002
    if "_v" in name:
        parts = name.split("_")
        cleaned_parts = []
        for part in parts:
            if part.startswith("v") and part[1:].isdigit():  # v001, v23, etc.
                break  # stop here, remove this and everything after
            cleaned_parts.append(part)
        new_name = "_".join(cleaned_parts)
        sepparator = "_"

    # Case 2: filenames like bla.001 (only checks the LAST dot)
    elif "." in name:
        base, last = name.rsplit(".", 1)  # split only once, from the right
        if last.isdigit():  # last part is just numbers like 001
            new_name = base
        else:
            new_name = name
        sepparator = "."

    # Case 3: filenames like object_mn_0002
    elif "_" in name:
        parts = name.split("_")
        if parts[-1].isdigit():  # last part is just digits
            parts = parts[:-1]  # drop the number
            new_name = "_".join(parts)
            sepparator = "_"

    master_name = f"{new_name}{sepparator}{appendix}{ext}"
    return master_name


def scale_png_by_half(input_path):
    """
    Scale a PNG image down by 2x and save it as '<filename>_low.png'
    next to the original file.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_low.png"

    with Image.open(input_path) as img:
        new_size = (max(1, img.width // 2), max(1, img.height // 2))
        resized = img.resize(new_size, Image.Resampling.LANCZOS)
        resized.save(output_path, format="PNG")

    return output_path


def publish_file(msg, path, data_object=None):
    ctx = ap.get_context()

    # load the existing history from shared settings
    project_settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings"
    )
    workspace_settings = aps.SharedSettings(
        ctx.workspace_id, "inc_workspace_settings")
    history_array = cast(list, project_settings.get("inc_versions", []))

    # Check if we need to create a master file
    create_master = isinstance(data_object, dict) and data_object.get(
        "create_master", False
    )

    # Check if we need to attach a thumbnail
    thumbnail = isinstance(data_object, dict) and data_object.get(
        "attached_doc_thumbnail", False
    )
    low_res_thumbnail = ""

    # Set the file status to Modified
    file_status = "Modified"
    # Create a random id
    version_id = uuid.uuid4().hex[:8]

    files = [{"path": path, "status": file_status}]

    # Set the application type based on the file extension
    type = ""
    ext = os.path.splitext(path)[1].lower()  # get file extension

    match ext:
        case ".c4d":
            type = "cinema4d"
        case ".mb" | ".ma":
            type = "maya"
        case ".blend":
            type = "blender"
        case _:
            type = ""

    # Build the json object that will be stored in the shared settings
    json_object = {
        "user_email": ctx.email,
        "message": msg,
        "time": str(datetime.now()),
        "id": version_id,
        "type": type,
        "files": files,
    }

    # Add the new entry to the history and store it
    json_object_str = json.dumps(json_object)
    history_array.append(json_object_str)
    project_settings.set("inc_versions", history_array)
    project_settings.store()

    # Attach a thumbnail to the increment
    if thumbnail:
        low_res_thumbnail = scale_png_by_half(thumbnail)
        aps.attach_thumbnails(path, low_res_thumbnail, thumbnail)

    if create_master:
        # Set some attributes on the master file
        database = ap.get_api()
        appendix = project_settings.get("master_file_appendix", "master")
        # Update the master file
        master_filename = get_master_filename(path, appendix)
        master_path = os.path.join(os.path.dirname(path), master_filename)
        aps.copy_file(path, master_path, True)

        # Attach a thumbnail to the master
        if thumbnail:
            aps.attach_thumbnails(master_path, low_res_thumbnail, thumbnail)

        file_base_name = os.path.splitext(os.path.basename(path))[0]
        # Set the source file name (the one with the increment)
        database.attributes.set_attribute_value(
            master_path, "Source File", file_base_name
        )

        # Mark it as a master with a tag for better visibility
        tag = aps.AttributeTag("master", "yellow")
        database.attributes.set_attribute_value(master_path, "Type", tag)

    # Trigger webhook if set -> needs a fix
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
                    {"path": path, "status": file_status},
                ],
            }

            requests.post(webhook_url, json=payload)
        except Exception as e:
            raise Exception(f"Failed to send webhook: {e}")

    return True
