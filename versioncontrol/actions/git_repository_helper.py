import anchorpoint as ap
import apsync as aps
from typing import Optional

CHANNEL_ID = "Git"

def update_project(
        repo_path: str, 
        remote_url: Optional[str], 
        is_join: bool, 
        project_id: str,
        workspace_id: str, 
        timeline_channel, 
        project):

    if not is_join:
        ap.add_path_to_project(repo_path, project_id, workspace_id)

        channel = aps.TimelineChannel()
        channel.id = CHANNEL_ID
        channel.name = "Git Repository"
        channel.icon = aps.Icon(":/icons/versioncontrol.svg", "#D4AA37")

        folder_id = aps.get_folder_id(repo_path)

        metadata = {"gitPathId": folder_id}
        if remote_url:
            metadata["gitRemoteUrl"] = remote_url

        channel.metadata = metadata

        if not timeline_channel:
            aps.add_timeline_channel(project, channel)
            
        aps.set_folder_icon(repo_path, aps.Icon(":/icons/versioncontrol.svg", "#f3d582"))
    else:
        ap.join_project_path(repo_path, project_id, workspace_id)
    pass
