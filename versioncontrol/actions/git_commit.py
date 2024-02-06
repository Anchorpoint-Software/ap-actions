import anchorpoint as ap
import apsync as aps

import sys, os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from git_push import sync_changes
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
import git_repository_helper as helper
if parent_dir in sys.path:
    sys.path.remove(parent_dir)

def update_gitignore_settings(dialog: ap.Dialog, value, path):
    settings = aps.Settings("gitignore_check")
    settings.set(path, value) 
    settings.store()

def check_missing_gitignore(repo, is_game_project, has_gitignore):
    if has_gitignore or not is_game_project: return True

    path = repo.get_root_path()
    settings = aps.Settings("gitignore_check")
    if settings.get(path, False):
        return True
    
    all_files = repo.get_all_files()
    for file in all_files:
        if file.endswith(".gitignore"):
            return True

    d = ap.Dialog()
    d.title = "Missing .gitignore file"
    d.icon = ":/icons/versioncontrol.svg"
    d.add_text("Anchorpoint could not find a <b>.gitignore</b> file in your project.<br>Because of this, too many files would be committed")
    d.add_info("Add a <a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/git/1-Git-basics/?highlight#gitignore'>.gitignore</a> file and commit again.")
    d.add_checkbox(callback=lambda d,v: update_gitignore_settings(d,v,path), var="neveraskagain", text="Disable this check")
    d.add_button("Close", callback=lambda d: d.close())
    d.show()

    return False

def stage_files(changes, all_files_selected, repo, lfs, progress, track_binary_files = True):
    def lfs_progress_callback(current, max):
        if progress.canceled:
            return False
        if max > 0:
            progress.report_progress(current / max)
        return True

    has_gitignore = False
    is_game_project = False
    gameextensions_to_check = {".umap", ".uasset", ".uproject", ".unity", ".unityproj"}

    to_stage = []
    for change in changes:
        if ".gitignore" in change.path:
            has_gitignore = True
        
        split = os.path.splitext(change.path)
        if len(split) > 1:
            ext = split[1].lower()
            if ext in gameextensions_to_check:
                is_game_project = True

        if change.selected:
            to_stage.append(change.path)

    if len(to_stage) == 0:
        return

    if not check_missing_gitignore(repo, is_game_project, has_gitignore):
        print("missing gitignore")
        return

    if track_binary_files:
        progress.set_text("Finding binary files")
        lfs.lfs_track_binary_files(to_stage, repo, lfs_progress_callback)
        if progress.canceled: 
            return

    progress.stop_progress()
    progress.set_text("Preparing your files to be committed. This may take some time")

    def progress_callback(current, max):
        if progress.canceled:
            return False
        progress.set_text("Staging files")
        if max > 0:
            progress.report_progress(current / max)

        return True

    try:
        repo.sync_staged_files(to_stage, all_files_selected, progress_callback)
    except Exception as e:
        submodule_error = False
        submodule_location = ""
        for change in to_stage:
            if os.path.isdir(change):
                gitdir = os.path.join(change, ".git")
                if os.path.exists(gitdir):
                    submodule_error = True
                    submodule_location = gitdir
                    break
        
        if submodule_error:
            rel_path = os.path.relpath(submodule_location,repo.get_root_path())
            d = ap.Dialog()
            d.title = "Your project contains more than one Git repository"
            d.icon = ":/icons/versioncontrol.svg"
            d.add_text(f"A folder in your project contains another Git repository and Git submodules<br>are currently not supported by Anchorpoint.<br><br>To resolve the issue, do the following:<ol><li>Backup the folder <b>{os.path.dirname(rel_path)}</b></li><li>Delete the hidden .git folder: <b>{rel_path}</b></li><li>Commit again</li></ol><br>Do not touch the .git folder in your project root!")
            d.show()
        else:
            raise e
    
def delay(func, progress, *args, **kwargs):
    import time
    time.sleep(1)
    if progress: progress.finish()
    func(*args, **kwargs)

def commit_auto_push(ctx, channel_id: str):
    sync_changes(channel_id, ctx)

def handle_git_autolock(repo, ctx, changes):
    locks = ap.get_locks(ctx.workspace_id, ctx.project_id)
    lock_map = {}
    for lock in locks:
        if "type" in lock.metadata and lock.metadata["type"] == "git":
            lock_map[lock.path] = lock

    patched_locks = []
    commit_id = repo.get_current_change_id()
    branch = repo.get_current_branch_name()

    def process_changes(changes):
        for change in changes:
            path = change.old_path if change.old_path else change.path
            path = os.path.join(repo.get_root_path(), path).replace("\\","/")
            if path in lock_map:
                lock = lock_map[path]
                metadata = lock.metadata
                metadata["gitcommit"] = commit_id
                metadata["gitbranch"] = branch
                lock.metadata = metadata
                patched_locks.append(lock)

    process_changes(changes.modified_files)
    process_changes(changes.deleted_files)
    process_changes(changes.renamed_files)
    
    try:
        ap.update_locks(ctx.workspace_id, ctx.project_id, patched_locks)
    except Exception as e:
        print(f"Failed to update locks: {str(e)}")

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    import git_lfs_helper as lfs
    if action_id != "gitcommit": return False
    ui = ap.UI()
    
    from git_settings import GitAccountSettings, GitProjectSettings
    from git_push import push_in_progress

    git_settings = GitAccountSettings(ctx)

    progress = ap.Progress("Committing Files", "Depending on your file count and size this may take some time", show_loading_screen=True, cancelable=True)
    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return

        auto_push = git_settings.auto_push_enabled() and repo.has_remote()
        auto_track_lfs = GitProjectSettings(ctx).lfsautotrack_enabled()

        stage_files(changes, all_files_selected, repo, lfs, progress, auto_track_lfs)
        if progress.canceled:
            ui.show_success("commit canceled")
            return
        
        progress.stop_progress()
        progress.set_text("Creating the commit. This may take some time")

        staged = repo.get_pending_changes(staged=True)
        changecount = staged.size()
        if changecount == 0:
            ui.show_info("Nothing to commit")
            return

        if len(ctx.username) > 0 and len(ctx.email) > 0:
            repo.set_username(ctx.username, ctx.email, ctx.project_path)
        else:
            ui.show_info("Cannot set username", "Please restart Anchorpoint and try again")
            return True

        repo.commit(message)
        repo.handle_sparse_checkout_after_commit(staged, progress=helper.SparseProgress(progress))
        handle_git_autolock(repo, ctx, staged)

        if auto_push and not push_in_progress(repo.get_git_dir()):
            # Queue async to give Anchorpoint a chance to update the timeline
            ap.get_context().run_async(delay, commit_auto_push, progress, ctx, channel_id)
        else:
            ap.close_timeline_sidebar()
            ui.show_success("Commit succeeded")
        
    except Exception as e:
        import git_errors
        if not git_errors.handle_error(e):
            print(str(e))
            ui.show_error("Commit Failed", str(e).splitlines()[0])
            raise e
    finally:
        ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)
        ap.UI().reload_tree()
        return True