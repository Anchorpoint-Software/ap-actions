from dataclasses import dataclass
from datetime import datetime
import os
from typing import Optional, cast

import anchorpoint as ap
import apsync as aps
import json


# A cache object so that we can re-use the history data
# without having to read it from shared settings every time
@dataclass
class IncCache:
    history_data: Optional[list] = None


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
def get_history_data(ctx):
    # This is how the stored data is formatted
    # [
    # {
    #        "user_email": "m.niedoba@anchorpoint.app",
    #        "message": "Added splinter for review.",
    #        "time": "2025-08-21T11:20:00",
    #        "id": "e5f6g7h8",
    #        "type": "version",
    #        "files": [
    #            {"path": "3_Scenes/1_Cinema4D/AB123_v001.c4d",
    #                "status": "Modified"}
    #        ]
    #    }
    # ]

    # Retrieve the history from shared settings
    settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings")

    # Get the array of strings and parse them as JSON objects
    history_array = cast(list, settings.get("inc_versions", []))
    history = []
    for entry in history_array:
        try:
            history.append(json.loads(entry))
        except:
            pass

    return history


# Map the history data to timeline entries
def get_history(ctx):
    # pyright: ignore[reportAssignmentType]
    cache: IncCache = ap.get_cache(
        "inc_cache" + ctx.project_id, default=IncCache())
    cache.history_data = get_history_data(ctx)

    # Build the timeline entries from the JSON history that comes from get_history()
    history = []
    for history_item in cache.history_data:
        entry = ap.TimelineChannelEntry()
        entry.id = history_item["id"]
        entry.time = int(datetime.fromisoformat(
            history_item["time"]).timestamp())
        entry.message = history_item["message"]
        entry.user_email = history_item["user_email"]
        entry.has_details = True

        if history_item["type"] == "cinema4d":
            entry.icon = aps.Icon(
                ":/icons/organizations-and-products/c4d.svg", "#F3D582"
            )
            entry.tooltip = "Published from Cinema 4D"
        elif history_item["type"] == "maya":
            entry.icon = aps.Icon(
                ":/icons/organizations-and-products/maya.svg", "#F3D582"
            )
            entry.tooltip = "Published from Maya"
        elif history_item["type"] == "blender":
            entry.icon = aps.Icon(
                ":/icons/organizations-and-products/blender.svg", "#F3D582"
            )
            entry.tooltip = "Published from Blender"
        else:
            entry.icon = aps.Icon(
                ":/icons/user-interface/information.svg", "#70717A")
            entry.tooltip = "Created a new file"

        history.append(entry)
    return history

# Initial load of the entire timeline


def on_load_timeline_channel(channel_id: str, page_size: int, ctx):
    if channel_id != "inc-vc-basic":
        return None

    info = ap.TimelineChannelInfo(ctx.project_id)
    history = get_history(ctx)
    has_more = False
    changes = None

    return info, changes, history, has_more


# Only load the timeline channel entries
def on_load_timeline_channel_entries(channel_id: str, page_size: int, page: int, ctx):
    if channel_id != "inc-vc-basic":
        return None, False
    history = get_history(ctx)
    return history, False


# Load the files when the user clicks on a timeline entry
def on_load_timeline_channel_entry_details(channel_id: str, entry_id: str, ctx):
    if channel_id != "inc-vc-basic":
        return None

    history_data: Optional[list] = None

    # pyright: ignore[reportAssignmentType]
    cache: Optional[IncCache] = ap.get_cache(
        "inc_cache" + ctx.project_id, default=None)
    if not cache:
        history_data = get_history_data(ctx)
    else:
        history_data = cache.history_data

    if not history_data:
        return None

    # Find the history item matching the entry_id
    history_item = next(
        (item for item in history_data if item["id"] == entry_id), None)
    if not history_item:
        return None

    # List all the changed files. In most cases it should just be one file
    changes = []
    for file_obj in history_item["files"]:
        change = ap.VCPendingChange()
        # make an absolute path
        change.path = os.path.join(
            ctx.project_path, file_obj["path"].replace("\\\\", "/"))
        change.status = get_vc_file_status_from_string(file_obj["status"])
        changes.append(change)

    details = ap.TimelineChannelEntryVCDetails()
    details.changes = ap.VCChangeList(changes)

    return details


# Only load channel info object
def on_load_timeline_channel_info(channel_id: str, ctx):
    if channel_id != "inc-vc-basic":
        return None

    info = ap.TimelineChannelInfo(ctx.project_id)
    return info


# listen to changes to refresh the timeline.
def on_settings_changed(workspace_id, project_id, settings_id, ctx):
    if settings_id != "inc_settings" or project_id != ctx.project_id:
        return

    history = get_history(ctx)
    ap.update_timeline_entries(
        "inc-vc-basic",
        ctx.project_id,
        history,
        has_more=False,
        update=True,
    )
