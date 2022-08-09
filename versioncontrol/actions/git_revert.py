import anchorpoint as ap
import apsync as aps

import sys, os, importlib
current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(current_dir, ".."))
sys.path.insert(0, current_dir)

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path

def revert(channel_id, project_path, dialog):
    ui = ap.UI()
    progress = ap.Progress("Reverting Files", show_loading_screen=True)
    
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo: return

    new_files = dialog.get_value("newfiles")
    try:
        repo.restore_all_files()
        if new_files:
            repo.clean()
    except:
        pass
    
    ap.refresh_timeline_channel(channel_id)
    ui.show_success("Revert Successful")

    dialog.close()

def button_pressed(channel_id, project_path, dialog):
    ctx = ap.Context.instance()
    ctx.run_async(revert, channel_id, project_path, dialog)

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, ctx):
    if action_id != "gitrevertall": return False

    dialog = ap.Dialog()
    dialog.title = "Revert Files"
    dialog.add_text("Do you really want to revert <b>all</b> modified files?<br>This cannot be undone.")
    dialog.add_checkbox(default=False, var="newfiles").add_text("Revert New Files")
    dialog.add_button("Yes", callback=lambda d: button_pressed(channel_id, ctx.project_path, d))
    dialog.show()

    return True