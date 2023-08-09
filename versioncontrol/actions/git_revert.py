from logging import exception
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os, itertools
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
if script_dir in sys.path : sys.path.remove(script_dir)

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
        relative_selected_paths.add(relpath.replace("\\", "/"))
        utility.make_file_writable(path)
        if not utility.is_file_writable(path):
            error = f"error: unable to unlink '{relpath}':"
            if not git_errors.handle_error(error):
                ui.show_info("Could not revert files", f"A file is not writable: {relpath}", duration=6000)
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
                    rel_path = os.path.relpath(change.path, repo_root).replace("\\", "/")
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
        ap.vc_load_pending_changes(channel_id, True)
        ap.refresh_timeline_channel(channel_id)
    
    ui.show_success("Revert Successful")

def revert_button_pressed(channel_id, project_path, selected_files, changes, revert_all, dialog):
    ctx = ap.get_context()
    ctx.run_async(revert, channel_id, project_path, True, selected_files, changes, revert_all)
    dialog.close()

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    if action_id != "gitrevert": return False

    revert_all = len(changes) == len(ctx.selected_files)
    if len(ctx.selected_files) == 0:
        ap.UI().show_success("No Files Selected")
        return True

    dialog = ap.Dialog()
    dialog.title = "Confirm Reversion"
    dialog.icon = ":/icons/revert.svg"
    dialog.add_text("Choosing <b>Revert</b> will reset your selected files to the last saved state in your repository. <ul> <li>Deleted files will be restored</li><li>New created files will be deleted</li><li>Modified files will return to their previously saved state</li> </ul>")
    dialog.add_info("Attention, this command is not undoable. <a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/git/2-Git-commands/#revert'>Learn more about Revert</a>")
    dialog.add_button("Revert", callback=lambda d: revert_button_pressed(channel_id, ctx.project_path, ctx.selected_files, changes, revert_all, d)).add_button("Cancel",callback=lambda d: d.close(), primary=False)
    dialog.show()

    return True

def undo(path: str, entry_id: str, channel_id: str):
    ui = ap.UI()
    try:
        progress = ap.Progress("Undoing Commit", show_loading_screen=True)
        repo = GitRepository.load(path)
        repo.revert_changelist(entry_id)

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)

        ui.show_success("Undo succeeded")

    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Undo Failed", str(e))

def undo_files(path: str, files: list[str], entry_id: str, channel_id: str):
    ui = ap.UI()
    try:
        progress = ap.Progress("Undoing File Changes", show_loading_screen=True)
        repo = GitRepository.load(path)
        repo_root = repo.get_root_path()

        # Check if any file to revert is locked by an application
        relative_selected_paths = set()
        for path in files:
            relpath = os.path.relpath(path, repo_root)
            relative_selected_paths.add(relpath.replace("\\", "/"))
            utility.make_file_writable(path)
            if not utility.is_file_writable(path):
                error = f"error: unable to unlink '{relpath}':"
                if not git_errors.handle_error(error):
                    ui.show_info("Could not undo files", f"A file is not writable: {relpath}", duration=6000)
                return True
            
        changes = repo.get_changes_for_changelist(entry_id)
        paths_to_delete = []
        for added_file in changes.new_files:
            if added_file.path in relative_selected_paths:
                relative_selected_paths.remove(added_file.path)
                paths_to_delete.append(os.path.join(repo_root, added_file.path))

        if len(relative_selected_paths) > 0:
            repo.restore_files(list(relative_selected_paths), entry_id + "~")
        for path in paths_to_delete:
            os.remove(path)

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)

        ui.show_success("Undo succeeded")

    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Undo Failed", str(e))

def restore_files(path: str, files: list[str], entry_id: str, channel_id: str, keep_original: bool):
    ui = ap.UI()
    if len(files) == 0:
        ap.UI().show_success("No Files Selected")

    try:
        repo = GitRepository.load(path)
        repo_root = repo.get_root_path()

        progress = ap.Progress("Restoring Files", show_loading_screen=True)

        # Check if any file to revert is locked by an application
        relative_selected_paths = set()
        for path in files:
            relpath = os.path.relpath(path, repo_root)
            relative_selected_paths.add(relpath.replace("\\", "/"))
            utility.make_file_writable(path)
            if not keep_original and not utility.is_file_writable(path):
                error = f"error: unable to unlink '{relpath}':"
                if not git_errors.handle_error(error):
                    ui.show_info("Could not restore files", f"A file is not writable: {relpath}", duration=6000)
                return True
                
        changes = repo.get_changes_for_changelist(entry_id)
        for deleted_file in changes.deleted_files:
            if deleted_file.path in relative_selected_paths:
                relative_selected_paths.remove(deleted_file.path)

        if len(relative_selected_paths) == 0:
            ui.show_success("Nothing to restore")
            return

        changes = repo.get_all_pending_changes()
        pending_changes_count = changes.size()

        repo.restore_files(list(relative_selected_paths), entry_id, keep_original)

        changes = repo.get_all_pending_changes()
        if keep_original:
            restored_files = len(relative_selected_paths)
        else:
            restored_files = changes.size() - pending_changes_count
            
        if restored_files == 1:
            ui.show_success("Restore Successful", "One file has been restored")
        elif restored_files > 1:
            ui.show_success("Restore Successful", f"{restored_files} files have been restored")
        else:
            ui.show_info("Nothing to restore", "The files are already the selected version")

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)


    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Restore Failed", str(e))

def reset_commit(path, commit: HistoryEntry, channel_id):
    ui = ap.UI()
    try:
        progress = ap.Progress("Resetting Project", show_loading_screen=True)
        repo = GitRepository.load(path)
        if repo.has_pending_changes(True):
            ui.show_error("Cannot reset project", "You have changed files. Commit them and try again")
            return 
        
        if not repo.has_remote():
            ui.show_error("Cannot reset project", "Reset Project cannot be used with local repositories")
            return 

        repo.reset(commit.id, True)

        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)

        ui.show_success("Reset Succeeded")

    except Exception as e:
        if not git_errors.handle_error(e):
            logging.info(str(e))
            ui.show_error("Reset Failed", str(e))
    finally:
        ap.stop_timeline_channel_action_processing(channel_id, "gitresetproject")

def async_wrapper(func, dialog, *args, **kwargs):
    dialog.close()
    ap.get_context().run_async(func, *args, **kwargs)

def show_restore_files_dialog(path: str, files: list[str], entry_id: str, channel_id: str):
    if len(files) == 0:
        ap.UI().show_success("No Files Selected")
        return
    
    first_file_name = os.path.basename(files[0])
    file_name_split = os.path.splitext(first_file_name)
    if len(file_name_split) >= 1:
        file_restored = file_name_split[0] + "_restored" + file_name_split[1]
    else:
        file_restored = first_file_name + "_restored"

    
    dialog = ap.Dialog()
    dialog.title = "Restore Files"
    dialog.icon = ":/icons/restore.svg"
    dialog.add_text("Restored files show up as changed files. <br> They can overwrite the original version.")
    dialog.add_info(f"If you keep the original, <b>{first_file_name}</b> <br>will be restored as <b>{file_restored}</b>")
    dialog.add_button("Overwrite", primary=False, callback=lambda d: async_wrapper(restore_files, d, path, files, entry_id, channel_id, False)).add_button("Keep Original", primary=False, callback=lambda d: async_wrapper(restore_files, d, path, files, entry_id, channel_id, True))
    dialog.show()

def cancel_restore_project(dialog, channel_id: str):
    ap.stop_timeline_channel_action_processing(channel_id, "gitresetproject")
    dialog.close()

def show_restore_project_dialog(path: str, commit: HistoryEntry, channel_id: str):
    dialog = ap.Dialog()
    dialog.title = "Reset Project"
    dialog.icon = ":/icons/restoreproject.svg"
    dialog.add_text("This command will set all files in your project to this commit. You can <br>go back to the latest state by pulling from the remote repository.")
    dialog.add_button("Continue", callback=lambda d: async_wrapper(reset_commit, d, path, commit, channel_id)).add_button("Cancel", callback=lambda d: cancel_restore_project(d, channel_id), primary=False)
    dialog.show()

def on_timeline_detail_action(channel_id: str, action_id: str, entry_id: str, ctx: ap.Context):
    ui = ap.UI()
    if action_id == "gitrevertcommit":
        try:
            ap.timeline_channel_action_processing(channel_id, "gitrevertcommit", "Undoing Commit...")
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return

            if repo.has_pending_changes(True):
                ui.show_info("Cannot undo commit", "You have changed files. Commit them and try again")
                return True
            else:
                undo(path, entry_id, channel_id)
                ap.refresh_timeline_channel(channel_id)

        except Exception as e:
            if not git_errors.handle_error(e):
                logging.info(str(e))
                ui.show_error("Undo Failed", str(e))
        finally:
            ap.stop_timeline_channel_action_processing(channel_id, "gitrevertcommit")
            return True
    
    if action_id == "gitrestorecommitfiles":
        path = get_repo_path(channel_id, ctx.project_path)
        show_restore_files_dialog(path, ctx.selected_files, entry_id, channel_id)
        return True
    
    if action_id == "gitresetproject":
        try:
            ap.timeline_channel_action_processing(channel_id, "gitresetproject", "Resetting Project...")
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return

            if repo.has_pending_changes(True):
                ui.show_info("Cannot reset project", "You have changed files. Commit them and try again")
                return True
            else:    
                if platform.system() == "Windows":
                    from vc.apgit.utility import is_executable_running
                    from git_lfs_helper import LFSExtensionTracker
                    if is_executable_running(["unrealeditor.exe"]):
                        lfsExtensions = LFSExtensionTracker(repo)
                        if lfsExtensions.is_extension_tracked("umap") or lfsExtensions.is_extension_tracked("uasset"):
                            ap.UI().show_info("Cannot reset project", "Unreal Engine prevents resetting the project. Please close Unreal Engine and try again", duration = 10000)
                            return True

                commit = repo.get_history_entry(entry_id)
                show_restore_project_dialog(path, commit, channel_id)

        except Exception as e:
            ap.stop_timeline_channel_action_processing(channel_id, "gitresetproject")
            if not git_errors.handle_error(e):
                logging.info(str(e))
                ui.show_error("Reset Failed", str(e))
        finally:    
            return True

    
    if action_id == "gitrevertcommitfiles":
        try:
            path = get_repo_path(channel_id, ctx.project_path)
            repo = GitRepository.load(path)
            if not repo: return

            if repo.has_pending_changes(True):
                ui.show_info("Cannot undo files", "You have changed files. Commit them and try again")
                return True
            else:
                undo_files(path, ctx.selected_files, entry_id, channel_id)
                ap.refresh_timeline_channel(channel_id)

        except Exception as e:
            if not git_errors.handle_error(e):
                logging.info(str(e))
                ui.show_error("Undo Failed", str(e))
        finally:
            return True

    return False