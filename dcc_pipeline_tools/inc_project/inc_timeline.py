from datetime import datetime
import anchorpoint as ap
import apsync as aps
import json

# Use the string version of the enum from c++


def get_vc_file_status_from_string(status_str: str):
    mapping = {
        "Unknown": ap.VCFileStatus.Unknown,
        "New": ap.VCFileStatus.New,
        "Deleted": ap.VCFileStatus.Deleted,
        "Modified": ap.VCFileStatus.Modified,
        "Renamed": ap.VCFileStatus.Renamed,
        "Conflicted": ap.VCFileStatus.Conflicted,
    }
    return mapping.get(status_str, ap.VCFileStatus.Unknown)

# Retrieve the history from shared settings


def get_history():

    # This is how the stored data is formatted
    # [
    # {
    #        "user_email": "m.niedoba@anchorpoint.app",
    #        "message": "Added splinter for review.",
    #        "time": "2025-08-21T11:20:00",
    #        "id": "e5f6g7h8",
    #        "type": "version",
    #        "files": [
    #            {"path": "C:/Users/USERNAME/Desktop/Projects/AB123/3_Scenes/1_Cinema4D/AB123_v001.c4d",
    #                "status": "Modified"}
    #        ]
    #    }
    # ]

    # Retrieve the history from shared settings
    ctx = ap.get_context()
    settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings")

    # Get the array of strings and parse them as JSON objects
    history_array = settings.get("inc_versions", [])
    history = []
    for entry in history_array:
        try:
            history.append(json.loads(entry))
        except:
            pass

    return history

# Load the timeline channel entries


def on_load_timeline_channel_entries(
    channel_id: str, time_start: datetime, time_end: datetime, ctx
):
    if channel_id != "inc-vc-basic":
        return None, False

    # Build the timeline entries from the JSON history that comes from get_history()
    history = []
    for history_item in get_history():
        entry = ap.TimelineChannelEntry()
        entry.id = history_item["id"]
        entry.time = int(datetime.fromisoformat(
            history_item["time"]).timestamp())
        entry.message = history_item["message"]
        entry.user_email = history_item["user_email"]
        entry.has_details = True

        if history_item["type"] == "cinema4d":
            entry.icon = aps.Icon(
                ":/icons/organizations-and-products/c4d.svg", "#F3D582")
            entry.tooltip = "Published from Cinema 4D"
        else:
            entry.icon = aps.Icon(
                ":/icons/user-interface/information.svg", "#70717A")
            entry.tooltip = "Created a new file"

        history.append(entry)

    return history, False

# load the files when the user clicks on a timeline entry


def on_load_timeline_channel_entry_details(channel_id: str, entry_id: str, ctx):
    if channel_id != "inc-vc-basic":
        return None

    # Find the history item matching the entry_id
    history_item = next((item for item in get_history()
                        if item["id"] == entry_id), None)
    if not history_item:
        return None

    # List all the changed files. In most cases it should just be one file
    changes = []
    for file_obj in history_item["files"]:
        change = ap.VCPendingChange()
        change.path = file_obj["path"].replace("\\\\", "/")
        change.status = get_vc_file_status_from_string(file_obj["status"])
        changes.append(change)

    details = ap.TimelineChannelEntryVCDetails()
    details.changes = ap.VCChangeList(changes)

    return details


# needs to be removed, because it has to be here due to a bug
def on_load_timeline_channel_info(channel_id: str, ctx):
    if channel_id != "inc-vc-basic":
        return None

    info = ap.TimelineChannelInfo()
    return info

# listen to file change to refresh the timeline. It's not the best solution, but the easiest for now


def on_settings_changed(workspace_id, project_id, settings_id, ctx):
    ap.refresh_timeline_channel("inc-vc-basic")

# File watcher events


def on_project_directory_changed(ctx):
    return None
