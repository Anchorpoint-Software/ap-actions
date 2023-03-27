import anchorpoint as ap
import apsync as aps

import sys, os, importlib
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
if parent_dir in sys.path: sys.path.remove(parent_dir)
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

def show_push_failed(error: str, channel_id, project_path):
    d = ap.Dialog()
    d.title = "Could not Push"
    d.icon = ":/icons/versioncontrol.svg"

    if "This repository is over its data quota" in error:
        d.add_text("The GitHub LFS limit has been reached.")
        d.add_info("To solve the problem open your GitHub <a href=\"https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage\">Billing and Plans</a> page and buy more <b>Git LFS Data</b>.")
    else:
        from textwrap import TextWrapper
        d.add_text("Something went wrong, the Git push did not work correctly")
        error = "\n".join(TextWrapper(width=100).wrap(error))
        if error != "":
            d.add_text(error)

    def retry():
        ctx = ap.get_context()
        ctx.run_async(push_async, channel_id, project_path)
        d.close()

    d.add_button("Retry", callback=lambda d: retry()).add_button("Close", callback=lambda d: d.close(), primary=False)
    d.show()

def push_async(channel_id: str, project_path):
    ui = ap.UI()
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        progress = ap.Progress("Pushing Git Changes", cancelable=True)
        ap.timeline_channel_action_processing(channel_id, "gitpush", "Pushing...")
        repo.fetch()
        if repo.is_pull_required():
            ui.show_info("Cannot Push Changes", "There are newer changes on the server, you have to pull them first")
            ap.stop_timeline_channel_action_processing(channel_id, "gitpush")    
            ap.refresh_timeline_channel(channel_id)
            return
        show_push_failed("This repository is over its data quota", channel_id, project_path)    
        return
        state = repo.push(progress=PushProgress(progress))
        if state == UpdateState.CANCEL:
            ui.show_info("Push Canceled")
        elif state != UpdateState.OK:
            show_push_failed("", channel_id, project_path)    
        else:
            ui.show_success("Push Successful")
    except Exception as e:
        show_push_failed(str(e), channel_id, project_path)
    finally:
        progress.finish()
        ap.stop_timeline_channel_action_processing(channel_id, "gitpush")

    ap.refresh_timeline_channel(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id != "gitpush": return False
    ctx.run_async(push_async, channel_id, ctx.project_path)
    return True