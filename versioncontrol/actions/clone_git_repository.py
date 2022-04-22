import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

class CloneProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int):
        if operation_code == "downloading":
            self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")

def clone_repo_async(repo_path, url):
    try:
        progress = ap.Progress("Cloning Git Repository")
        repo = GitRepository.clone(url, repo_path, progress=CloneProgress(progress))
        progress.finish()
        ui.navigate_to_folder(repo_path)
        ui.show_success("Git Repository Cloned")
    except Exception as e:
        ui.show_error("Failed to clone Git Repository", str(e))

def clone_repo(dialog: ap.Dialog):
    name = dialog.get_value("name")
    url = dialog.get_value("url")
    repo_path = os.path.join(path, name)
    if GitRepository.is_repo(repo_path):
        ui.show_info("Already a Git repo")
    else:
        ctx.run_async(clone_repo_async, repo_path, url)
        dialog.close()

dialog = ap.Dialog()
dialog.title = "Clone a Git repository"
dialog.icon = ctx.icon
dialog.add_input(placeholder="Url", var="url")
dialog.add_input(placeholder="Repository Name", var="name")
dialog.add_button("Create", callback=clone_repo)
dialog.show()