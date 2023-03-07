from logging import exception
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(script_dir)

def delete_stash(path: str, channel_id):
    ui = ap.UI()
    try:
        progress = ap.Progress("Deleting Shelved Files", show_loading_screen=True)
        repo = GitRepository.load(path)

        stash = repo.get_branch_stash()
        if not stash:
            raise Exception("No Shelved Files Found")
        
        repo.drop_stash(stash)

        ui.show_success("Shelved files deleted")
        ap.close_timeline_sidebar()
        ap.refresh_timeline_channel(channel_id)
        ap.vc_load_pending_changes(channel_id)
    except Exception as e:
        ui.show_error("Could not delete shelved files", str(e))

def delete_button_pressed(path: str, channel_id, dialog):
    ctx = ap.Context.instance()
    dialog.close()
    ctx.run_async(delete_stash, path, channel_id)

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    if action_id != "gitstashfiles": 
         return False
    
    ui = ap.UI()

    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return
        progress = ap.Progress("Shelving Files", show_loading_screen=True)
        repo.stash(True)

        ui.show_success("Files shelved")
    except Exception as e:
            ui.show_error("Could not shelve files", str(e))
    finally:
            return True

def on_timeline_detail_action(channel_id: str, action_id: str, entry_id: str, ctx: ap.Context):
    ui = ap.UI()

    if action_id == "gitstashdrop":
        try:
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return

            dialog = ap.Dialog()
            dialog.title = "Delete Shelved Files"
            dialog.icon = ":/icons/trash.svg"
            dialog.add_text("This will <b>delete all files</b> in your shelf.<br>This cannot be undone.")
            dialog.add_empty()
            dialog.add_button("Delete Files", callback=lambda d: delete_button_pressed(path, channel_id, d)).add_button("Cancel", callback=lambda d: d.close())
            dialog.show()
            
        except Exception as e:
            ui.show_error("Could not delete shelved files", str(e))
        finally:
            return True
        
    if action_id == "gitstashapply":
        try:
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return
            
            progress = ap.Progress("Restoring Shelved Files", show_loading_screen=True)
            repo.pop_stash(None)

            ap.close_timeline_sidebar()
            ap.vc_load_pending_changes(channel_id)

            if repo.has_conflicts():
                ap.vc_resolve_conflicts(channel_id)

        except Exception as e:
            error = str(e)
            logging.info(error)
            if "already exists" in error:
                logging.info(f"Could not restore shelved files: ", str(e))
                ui.show_info("Could not restore all shelved files", "You have changed files that would be overwritten.", duration=6000)
            elif "CONFLICT" in error:
                logging.info(f"Could not restore shelved files due to conflict: ", str(e))
                ui.show_info("Shelved Files are Kept", "At least one file from the shelve is conflicting. We kept the shelved files in case you need it again", duration=15000)
            else:
                raise e
        finally:
            return True
    return False