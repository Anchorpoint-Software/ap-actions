import anchorpoint as ap
import apsync as aps

import sys, os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(parent_dir)

def stage_files(changes, all_files_selected, repo, lfs, progress):
    def lfs_progress_callback(current, max):
        if max > 0:
            progress.report_progress(current / max)

    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)

    progress.set_text("Finding binary files")
    lfs.lfs_track_binary_files(to_stage, repo, lfs_progress_callback)

    progress.stop_progress()
    progress.set_text("Preparing your files to be committed. This may take some time")

    def progress_callback(current, max):
        progress.set_text("Staging files")
        if max > 0:
            progress.report_progress(current / max)

    repo.sync_staged_files(to_stage, all_files_selected, progress_callback)

def commit_async(message: str, changes, all_files_selected, channel_id, project_path, lfs):
    ui = ap.UI()
    progress = ap.Progress("Committing Files", "Depending on your file count and size this may take some time", show_loading_screen=True)
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return
        stage_files(changes, all_files_selected, repo, lfs, progress)
        
        progress.stop_progress()
        progress.set_text("Creating the commit. This may take some time")

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

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    import git_lfs_helper as lfs
    if action_id != "gitcommit": return False
    ctx.run_async(commit_async, message, changes, all_files_selected, channel_id, ctx.project_path, lfs)
    return True