from threading import local
from git import GitCommandError
import anchorpoint as ap
import apsync as aps
import git_errors
import itertools

import sys, os, importlib

current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
from git_timeline import map_commit
if parent_dir in sys.path: sys.path.remove(parent_dir)
class PullProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        if operation_code == "downloading":
            if info_text:
                self.ap_progress.set_text(f"Downloading Files: {info_text}")
            else:
                self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

    def canceled(self):
        return self.ap_progress.canceled

def check_changes_writable(repo, changes):
    for change in itertools.chain(changes.new_files, changes.renamed_files, changes.modified_files, changes.deleted_files):
        path = os.path.join(repo.get_root_path(), change.path)
        if not utility.is_file_writable(path):
            error = f"error: unable to unlink '{change.path}':"
            if not git_errors.handle_error(error):
                ap.UI().show_info("Could not shelve files", f"A file is not writable: {change.path}", duration=6000)
            return False
    return True

def handle_files_to_pull(repo):
    from git_lfs_helper import LFSExtensionTracker
    lfsExtensions = LFSExtensionTracker(repo)

    changes = repo.get_files_to_pull(include_added=False)
    if not changes:
        return
    root_dir = repo.get_root_path()
    def make_readwrite(changes):
        for change in changes:
            path = root_dir + "/"+ change.path
            if not os.path.exists(path):
                continue

            if not lfsExtensions.is_file_tracked(path):
                continue

            utility.make_file_writable(path)
            
    make_readwrite(changes.modified_files)
    make_readwrite(changes.deleted_files)
    make_readwrite(changes.new_files)


def pull(repo: GitRepository, channel_id: str):
    lock_disabler = ap.LockDisabler()
    ui = ap.UI()
    progress = ap.Progress("Updating Git Changes", show_loading_screen=True, cancelable=False)
    handle_files_to_pull(repo)
    changes = repo.get_pending_changes(False)
    staged_changes = repo.get_pending_changes(True)
    
    stashed_changes = False
    if changes.size() > 0 or staged_changes.size() > 0:
        progress.set_text("Shelving Changed Files")
        if not check_changes_writable(repo, changes):
            return True
        if not check_changes_writable(repo, staged_changes):
            return True
            
        repo.stash(True)
        stashed_changes = True

    progress.set_cancelable(True)
    progress.set_text("Talking to Server")

    commits_to_pull = repo.get_history(remote_only=True)

    state = repo.update(progress=PullProgress(progress), rebase=False)
    progress.set_cancelable(False)

    def update_pulled_commits():
        if commits_to_pull and len(commits_to_pull) > 0:
            history = []
            for commit in commits_to_pull:
                commit.type = HistoryType.SYNCED
                history.append(map_commit(repo, commit))
            ap.update_timeline_channel_entries(channel_id, history)

    if state == UpdateState.NO_REMOTE:
        ui.show_info("Branch does not track a remote branch", "Push your branch first")    
        return False
    elif state == UpdateState.CONFLICT:
        ui.show_info("Conflicts detected", "Please resolve your conflicts")    
        update_pulled_commits()
        ap.refresh_timeline_channel(channel_id)
        progress.finish()
        return False
    elif state == UpdateState.CANCEL:
        ui.show_info("Pull Canceled")
        if stashed_changes:
            progress.set_text("Restoring Shelved Files")
            repo.pop_stash()
        return False
    elif state != UpdateState.OK:
        ui.show_error("Failed to update Git Repository")    
        return False
    else:
        if repo.is_merging():
            try:
                repo.continue_merge()
            except Exception as e:
                if "There is no merge in progress" in str(e):
                    pass
        
        if stashed_changes:
            progress.set_text("Restoring Shelved Files")
            repo.pop_stash()        
    
        update_pulled_commits()

    return True


def pull_async(channel_id: str, project_path):
    ui = ap.UI()
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return

        if pull(repo, channel_id):
            ui.show_success("Update Successful")
        
    except Exception as e:
        if not git_errors.handle_error(e):
            print(e)
            if "conflict" in str(e):
                if repo.is_merging():
                    ui.show_info("Conflicts detected", "Please resolve your conflicts or cancel the pull")    
                else:
                    ui.show_info("Conflicts detected", "Please resolve your conflicts")    
            else:
                ui.show_error("Failed to update Git Repository", "Please try again")    
                   
    ap.vc_load_pending_changes(channel_id, True)
    ap.refresh_timeline_channel(channel_id)

def resolve_conflicts(channel_id):
    ap.vc_resolve_conflicts(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id == "gitpull":
        ctx.run_async(pull_async, channel_id, ctx.project_path)
    if action_id == "gitcancelmerge":
        from git_conflicts import cancel_merge
        ctx.run_async(cancel_merge, channel_id, ctx.project_path)
        return True
    if action_id == "gitresolveconflicts": 
        ctx.run_async(resolve_conflicts, channel_id)
        return True
    return False