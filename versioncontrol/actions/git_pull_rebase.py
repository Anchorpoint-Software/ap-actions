from git import GitCommandError
import anchorpoint as ap
import apsync as aps

import sys, os, importlib
current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(current_dir, ".."))
sys.path.insert(0, current_dir)

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path

class PullProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int):
        print(operation_code)
        if operation_code == "writing":
            self.ap_progress.set_text("Uploading Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")

def pull_async(channel_id: str, project_path):
    ui = ap.UI()
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        progress = ap.Progress("Updating Git Changes", show_loading_screen=True)
        
        if repo.has_pending_changes() > 0:
            ui.show_info("Cannot pull", "You have to commit all your files before you can continue")
            return

        state = repo.update(progress=PullProgress(progress))
        if state == UpdateState.NO_REMOTE:
            ui.show_info("Branch does not track a remote branch", "Push your branch first")    
        elif state == UpdateState.CONFLICT:
            ui.show_info("Conflicts detected", "Please resolve your conflicts or abort the rebase")    
            ap.refresh_timeline_channel(channel_id)
            ap.vc_resolve_conflicts(channel_id)        
            progress.finish()
            return
        elif state != UpdateState.OK:
            ui.show_error("Failed to update Git Repository")    
        else:
            ui.show_success("Update Successful")
        progress.finish()
    except Exception as e:
        ui.show_error("Failed to update Git Repository", str(e))
        raise e
    ap.refresh_timeline_channel(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id != "gitpullrebase": return
    ctx.run_async(pull_async, channel_id, ctx.project_path)