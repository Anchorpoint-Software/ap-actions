import anchorpoint as ap
import apsync as aps

import sys, os, importlib
current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(current_dir, ".."))
sys.path.insert(0, current_dir)

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path

def stage_files(changes, repo):
    import git_lfs_helper as lfs
    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)
    
    lfs.lfs_track_binary_files(to_stage, repo)
    repo.sync_staged_files(to_stage)

def commit_async(message: str, changes, channel_id, project_path):
    ui = ap.UI()
    progress = ap.Progress("Committing Files", show_loading_screen=True)
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        stage_files(changes, repo)

        staged = repo.get_pending_changes(staged=True)
        changecount = staged.size()
        if changecount == 0:
            ui.show_info("Nothing to commit")
            return

        repo.commit(message)
        ui.show_success("Commit succeeded")
    except Exception as e:
        ui.show_error("Commit Failed", str(e))

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, ctx):
    if action_id != "gitcommit": return
    ctx.run_async(commit_async, message, changes, channel_id, ctx.project_path)