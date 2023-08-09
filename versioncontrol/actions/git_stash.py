from logging import exception
import anchorpoint as ap
import apsync as aps
import git_errors
import itertools

import sys, os
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
if script_dir in sys.path: sys.path.remove(script_dir)

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
    ctx = ap.get_context()
    dialog.close()
    ctx.run_async(delete_stash, path, channel_id)

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    if action_id != "gitstashfiles": 
         return False
    
    ui = ap.UI()

    if len(ctx.selected_files) == 0:
        ui.show_success("No Files Selected")
        return True

    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return
        progress = ap.Progress("Shelving Files", show_loading_screen=True)

        stash_all = len(changes) == len(ctx.selected_files)
        
        # Check if any file to stash is locked by an application
        relative_selected_files = []
        for path in ctx.selected_files:
            relpath = os.path.relpath(path, repo.get_root_path())
            relative_selected_files.append(relpath)
            if not utility.is_file_writable(path):
                error = f"error: unable to unlink '{relpath}':"
                if not git_errors.handle_error(error):
                    ui.show_info("Could not shelve files", f"A file is not writable: {relpath}", duration=6000)
                return True

        if stash_all:
            repo.stash(True)
        else:
            repo.stash(True, relative_selected_files)

        ap.vc_load_pending_changes(channel_id, True)
        ap.refresh_timeline_channel(channel_id)
        ui.show_success("Files shelved")
    except Exception as e:
        if not git_errors.handle_error(e):
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
            dialog.title = "Clear Shelved Files"
            dialog.icon = ":/icons/trash.svg"
            dialog.add_text("Are you sure to <b>remove all files</b><br>in the shelf. This cannot be undone.")
            dialog.add_info("Learn more about <a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/git/4-Resolving-conflicts/#shelved-files'>Shelved Files</a>")
            dialog.add_button("Clear", callback=lambda d: delete_button_pressed(path, channel_id, d)).add_button("Cancel", callback=lambda d: d.close(), primary=False)
            dialog.show()
            
        except Exception as e:
            if not git_errors.handle_error(e):
                ui.show_error("Could not delete shelved files", str(e))
        finally:
            return True
        
    if action_id == "gitstashapply":
        try:
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return
            
            if repo.has_pending_changes(True):
                ap.UI().show_info("Could not restore shelved files", "You have changed files that could be overwritten. Commit them and try again", duration=6000)

            progress = ap.Progress("Restoring Shelved Files", show_loading_screen=True)

            stash = repo.get_branch_stash()

            # Check if any file in the stash is locked by an application
            changes = repo.get_stash_changes(stash)
            for change in itertools.chain(changes.new_files, changes.renamed_files, changes.modified_files, changes.deleted_files):
                path = os.path.join(repo.get_root_path(), change.path)
                if not utility.is_file_writable(path):
                    error = f"error: unable to unlink '{change.path}':"
                    if not git_errors.handle_error(error):
                        ui.show_info("Could not restore shelved files", f"A file is not writable: {change.path}", duration=6000)
                    return True

            repo.pop_stash(stash)

            ap.close_timeline_sidebar()
            ap.vc_load_pending_changes(channel_id)

        except Exception as e:
            error = str(e)
            print(error)
            if not git_errors.handle_error(e):
                if "already exists" in error:
                    logging.info(f"Could not restore shelved files: ", str(e))
                    ui.show_info("Could not restore all shelved files", "You have changed files that would be overwritten.  We kept the shelved files in case you need it again", duration=15000)
                elif "CONFLICT" in error:
                    logging.info(f"Could not restore shelved files due to conflict: ", str(e))
                    ui.show_info("Shelved Files are Kept", "At least one file from the shelve is conflicting. We kept the shelved files in case you need it again", duration=15000)
                else:
                    raise e
        finally:
            return True
    return False
