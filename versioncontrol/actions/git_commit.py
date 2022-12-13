import anchorpoint as ap
import apsync as aps

import sys, os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(parent_dir)

def stage_files(changes, repo, lfs, progress):
    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)

    lfs.lfs_track_binary_files(to_stage, repo)

    progress.set_text("Adding files to your commit")
    def progress_callback(current, max):
        progress.report_progress(current / max)

    repo.sync_staged_files(to_stage, progress_callback)

def commit_async(message: str, changes, channel_id, project_path, lfs):
    ui = ap.UI()
    progress = ap.Progress("Committing Files", "Depending on your file count and size this may take some time", show_loading_screen=True)
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        stage_files(changes, repo, lfs, progress)
        progress.set_text("Finalizing...")

        staged = repo.get_pending_changes(staged=True)
        changecount = staged.size()
        if changecount == 0:
            ui.show_info("Nothing to commit")
            return

        repo.commit(message)
        ui.show_success("Commit succeeded")
        if "vc_load_pending_changes" in dir(ap):
            ap.vc_load_pending_changes("Git")    
        ap.refresh_timeline_channel("Git")
        
    except Exception as e:
        ui.show_error("Commit Failed", str(e))
        raise e

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, ctx):
    import git_lfs_helper as lfs
    if action_id != "gitcommit": return False
    ctx.run_async(commit_async, message, changes, channel_id, ctx.project_path, lfs)
    return True