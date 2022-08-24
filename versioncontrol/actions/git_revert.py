import anchorpoint as ap
import apsync as aps

import sys, os
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(script_dir)

def revert(channel_id, project_path, dialog):
    ui = ap.UI()
    progress = ap.Progress("Reverting Files", show_loading_screen=True)
    
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo: return

    new_files = dialog.get_value("newfiles")
    try:
        repo.unstage_all_files()
        repo.restore_all_files()
        if new_files:
            repo.clean()
    except:
        pass
    
    ap.refresh_timeline_channel(channel_id)
    ui.show_success("Revert Successful")

    dialog.close()

def revert_button_pressed(channel_id, project_path, dialog):
    ctx = ap.Context.instance()
    ctx.run_async(revert, channel_id, project_path, dialog)

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, ctx):
    if action_id != "gitrevertall": return False

    dialog = ap.Dialog()
    dialog.title = "Revert Files"
    dialog.add_text("Do you really want to revert <b>all</b> modified files?<br>This cannot be undone.")
    dialog.add_checkbox(default=False, var="newfiles").add_text("Revert New Files")
    dialog.add_button("Yes", callback=lambda d: revert_button_pressed(channel_id, ctx.project_path, d))
    dialog.show()

    return True

def undo(path: str, entry_id: str):
    try:
        progress = ap.Progress("Reverting Commit", show_loading_screen=True)
        repo = GitRepository.load(path)
        repo.revert_changelist(entry_id)

        ui = ap.UI()
        ui.show_success("Revert succeeded")
    except Exception as e:
        ui.show_error("Revert Failed", str(e))

def undo_button_pressed(path: str, entry_id: str, dialog):
    ctx = ap.Context.instance()
    dialog.close()
    ctx.run_async(undo, path, entry_id)

def on_timeline_detail_action(channel_id: str, action_id: str, entry_id: str, ctx: ap.Context):
    if action_id != "gitrevertcommit": return False
    ui = ap.UI()

    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if repo.has_pending_changes(True):
            dialog = ap.Dialog()
            dialog.title = "Undo Commit"
            dialog.add_text("You have uncommitted changes. Undoing all changes from this commit<br> might overwrite local changes. This cannot be undone.")
            dialog.add_empty()
            dialog.add_button("Continue", callback=lambda d: undo_button_pressed(path, entry_id, d)).add_button("Cancel", callback=lambda d: d.close())
            dialog.show()
        else:
            print("no uncp0m.")
            undo(path, entry_id)
            ap.refresh_timeline_channel(channel_id)
    except Exception as e:
        ui.show_error("Revert Failed", str(e))