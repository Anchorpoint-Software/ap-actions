import anchorpoint as ap
import apsync as aps
from typing import Optional

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
import vc.versioncontrol_interface as vc

CHANNEL_ID = "Git"

def update_project(
        repo_path: str, 
        remote_url: Optional[str], 
        is_join: bool, 
        timeline_channel, 
        project: aps.Project, 
        add_path: bool = True):

    if not is_join:
        if add_path:
            ap.add_path_to_project(repo_path, project.id, project.workspace_id)

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
        update_project_join(repo_path, project.id, project.workspace_id)
    pass

def update_project_join(
        repo_path: str, 
        project_id: str,
        workspace_id: str):

    ap.join_project_path(repo_path, project_id, workspace_id)

class CloneProgress(vc.Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        if operation_code == "downloading":
            if info_text:
                self.ap_progress.set_text(f"Downloading Files: {info_text}")
            else:
                self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()
