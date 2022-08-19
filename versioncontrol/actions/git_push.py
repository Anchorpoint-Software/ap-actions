import anchorpoint as ap
import apsync as aps

import sys, os, importlib
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(parent_dir)
class PushProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        if operation_code == "writing":
            if info_text:
                self.ap_progress.set_text(f"Uploading Files: {info_text}")
            else:
                self.ap_progress.set_text("Uploading Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

def push_async(channel_id: str, project_path):
    ui = ap.UI()
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        progress = ap.Progress("Pushing Git Changes", cancelable=True)
        ap.timeline_channel_action_processing(channel_id, "gitpush", "Pushing...")
        state = repo.push(progress=PushProgress(progress))
        if state == UpdateState.CANCEL:
            ui.show_info("Push Canceled")
        elif state != UpdateState.OK:
            ui.show_error("Failed to push Git Repository")    
        else:
            ui.show_success("Push Successful")
    except Exception as e:
        ui.show_error("Failed to push Git Repository", str(e))
    finally:
        progress.finish()
        ap.stop_timeline_channel_action_processing(channel_id, "gitpush")

    ap.refresh_timeline_channel(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id != "gitpush": return False
    ctx.run_async(push_async, channel_id, ctx.project_path)
    return True