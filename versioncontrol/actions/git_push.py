import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

class PushProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int):
        if operation_code == "writing":
            self.ap_progress.set_text("Uploading Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")

def clone_repo_async():
    repo = GitRepository.load(path)
    if repo == None: return
    try:
        progress = ap.Progress("Pushing Git Changes")
        success = repo.push(progress=PushProgress(progress))
        if not success:
            ui.show_error("Failed to push Git Repository")    
        else:
            ui.show_success("Push Successful")
        progress.finish()
    except Exception as e:
        ui.show_error("Failed to push Git Repository", e)

ctx.run_async(clone_repo_async)