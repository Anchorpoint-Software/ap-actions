import anchorpoint as ap
import apsync as aps
from typing import Optional

import sys, os
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)
import vc.versioncontrol_interface as vc
if script_dir in sys.path: sys.path.remove(script_dir)

CHANNEL_ID = "Git"

def update_project(
        repo_path: str, 
        remote_url: Optional[str], 
        is_join: bool, 
        timeline_channel, 
        project: aps.Project, 
        add_path: bool = True):

    if not is_join:
        channel = aps.TimelineChannel()
        channel.id = CHANNEL_ID
        channel.name = "Git Repository"
        channel.icon = aps.Icon(":/icons/versioncontrol.svg", "#D4AA37")

        metadata = {}
        if remote_url:
            metadata["gitRemoteUrl"] = remote_url

        channel.metadata = metadata

        if not timeline_channel:
            aps.add_timeline_channel(project, channel)
    else:
        update_project_join(repo_path, project.id, project.workspace_id)
    pass

def update_project_join(
        repo_path: str, 
        project_id: str,
        workspace_id: str):

    ap.join_project_path(repo_path, project_id, workspace_id)

def folder_empty(folder_path):
    import platform
    content = os.listdir(folder_path)
    if len(content) == 0: return True
    if platform.system() == "Darwin" and len(content) == 1:
        # macOS .DS_Store causes git clone to fail even if the rest of the folder is empty
        ds_store = os.path.join(folder_path, ".DS_Store")
        if platform.system() == "Darwin" and os.path.exists(ds_store):
            os.remove(ds_store)
            return True

    return False

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

    def canceled(self):
        return self.ap_progress.canceled

class FetchProgress(vc.Progress):
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
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

    def canceled(self):
        return self.ap_progress.canceled