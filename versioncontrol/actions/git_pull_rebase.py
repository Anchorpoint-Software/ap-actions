from git import GitCommandError
import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

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

def pull_repo_async():
    repo = GitRepository.load(path)
    if repo == None: return
    try:
        progress = ap.Progress("Pulling Git Changes")
        state = repo.update(progress=PullProgress(progress))
        if state != UpdateState.OK:
            if state == UpdateState.CONFLICT:
                ui.show_info("Conflicts Detected")    
            else:
                ui.show_error("Error when pulling changes")
        else:
            ui.show_success("Pull Successful")
        progress.finish()
    except GitCommandError as e:
        ui.show_error("Failed to pull Git Repository", e.stderr, 10000)

ctx.run_async(pull_repo_async)