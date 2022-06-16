import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path

def stage_files(changes, repo):
    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)
    
    # TODO: Handle Git LFS
    # repo.unstage_files(to_unstage)
    repo.sync_staged_files(to_stage)

def commit_async(message: str, changes, repo):
    ui = ap.UI()
    try:
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
    ui = ap.UI()

    path = get_repo_path(channel_id, ctx.project_path)
    repo = GitRepository.load(path)
    if not repo: return

    ctx.run_async(commit_async, message, changes, repo)