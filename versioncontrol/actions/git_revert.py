from logging import exception
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os, itertools
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(script_dir)

def revert(channel_id, project_path, new_files, selected_files: list[str], changes, revert_all = False):
    ui = ap.UI()
    progress = ap.Progress("Reverting Files", show_loading_screen=True)
    
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo: return

    repo_root = repo.get_root_path()
    # Check if any file to revert is locked by an application
    relative_selected_paths = set()
    for path in selected_files:
        relpath = os.path.relpath(path, repo_root)
        relative_selected_paths.add(relpath)
        if not utility.is_file_writable(path):
            error = f"error: unable to unlink '{relpath}':"
            if not git_errors.handle_error(error):
                ui.show_info("Could not shelve files", f"A file is not writable: {relpath}", duration=6000)
            return True
        
    try:
        try:
            if revert_all:
                repo.unstage_all_files()
                repo.restore_all_files()
                if new_files:
                    repo.clean()
            else:
                staged_changes = repo.get_pending_changes(True)
                paths_to_unstage = []
                paths_to_delete = []
                paths_to_revert = []
                for change in itertools.chain(staged_changes.new_files, staged_changes.renamed_files, staged_changes.modified_files, staged_changes.deleted_files):
                    if change.path in relative_selected_paths:
                        paths_to_unstage.append(change.path)

                for change in changes:
                    rel_path = os.path.relpath(change.path, repo_root)
                    if rel_path in relative_selected_paths:
                        if change.status == ap.VCFileStatus.New:
                            paths_to_delete.append(change.path)
                        else:
                            paths_to_revert.append(rel_path)
                
                if len(paths_to_unstage) > 0:
                    repo.unstage_files(paths_to_unstage)
                repo.restore_files(paths_to_revert)
                for path in paths_to_delete:
                    os.remove(path)

        except Exception as e:
            if git_errors.handle_error(e):
                ui.show_error("Could not revert files")
                return
            raise e

        
    except Exception as e:
        git_errors.handle_error(e)
        ui.show_error("Could not revert files")
        print(str(e))
        return
    finally:
        try:
            ap.vc_load_pending_changes(channel_id, True)
        except:
            ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)
    
    ui.show_success("Revert Successful")

def revert_button_pressed(channel_id, project_path, selected_files, changes, revert_all, dialog):
    ctx = ap.get_context()
    ctx.run_async(revert, channel_id, project_path, True, selected_files, changes, revert_all)
    dialog.close()

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    if action_id != "gitrevert": return False

    revert_all = len(changes) == len(ctx.selected_files)

    dialog = ap.Dialog()
    dialog.title = "Revert Files"
    dialog.icon = ":/icons/revert.svg"
    dialog.add_text("Do you really want to revert the selected files?<br>This cannot be undone.")
    dialog.add_button("Continue", callback=lambda d: revert_button_pressed(channel_id, ctx.project_path, ctx.selected_files, changes, revert_all, d)).add_button("Cancel",callback=lambda d: d.close(), primary=False)
    dialog.show()

    return True

def undo(path: str, entry_id: str, channel_id: str, shelve: bool):
    ui = ap.UI()
    try:
        progress = ap.Progress("Undoing Commit", show_loading_screen=True)
        repo = GitRepository.load(path)

        if shelve:
            repo.stash(True)

        repo.revert_changelist(entry_id)

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)

        if shelve:
            ui.show_success("Undo succeeded", "We have shelved all your changed files")
        else:
            ui.show_success("Undo succeeded")

    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Undo Failed", str(e))

def on_timeline_detail_action(channel_id: str, action_id: str, entry_id: str, ctx: ap.Context):
    if action_id != "gitrevertcommit": return False
    ui = ap.UI()

    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if repo.has_pending_changes(True):
            ui.show_info("Cannot undo commit", "You have changed files. Commit them and try again")
            return True
        else:
            undo(path, entry_id, channel_id, False)
            ap.refresh_timeline_channel(channel_id)

    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Undo Failed", str(e))
    finally:
        return True