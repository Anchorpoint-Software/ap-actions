from git import GitCommandError
import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 
from vc.models import ConflictResolveState

def cancel_rebase(channel_id, project_path):
    from vc.apgit.utility import get_repo_path
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo:
        return
    repo.abort_rebasing()
    ap.refresh_timeline_channel(channel_id)

def resolve_conflicts(channel_id):
    ap.vc_resolve_conflicts(channel_id)

def on_vc_resolve_conflicts(channel_id: str, conflict_handling: ap.VCConflictHandling, paths: Optional[list[str]], ctx):
    from vc.apgit.utility import get_repo_path
    
    project_path = ctx.project_path
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo:
        return

    if conflict_handling == ap.VCConflictHandling.Cancel:
        progress = ap.Progress("Canceling", show_loading_screen=True)
        cancel_rebase(channel_id, project_path)
    elif conflict_handling == ap.VCConflictHandling.External:
        progress = ap.Progress("Running External Program", show_loading_screen=True)
        repo.launch_external_merge("vscode", paths)    
    else:
        unstaged_files, staged_files = repo.get_deleted_files()
        if conflict_handling == ap.VCConflictHandling.TakeOurs:
            progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
            
            # git checkout --theirs (theirs and ours is inverse when rebasing)
            if len(staged_files) > 0:
                repo.remove_files(staged_files)
            repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)

        elif conflict_handling == ap.VCConflictHandling.TakeTheirs:
            progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
            
            # git checkout --ours (theirs and ours is inverse when rebasing)
            if len(unstaged_files) > 0:
                repo.remove_files(unstaged_files)
            repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)
    
    if repo.has_conflicts() == False and repo.is_rebasing():
        repo.continue_rebasing()

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id == "gitcancelrebase":
        ctx.run_async(cancel_rebase, channel_id, ctx.project_path)
        return True
    if action_id == "gitresolveconflicts": 
        ctx.run_async(resolve_conflicts, channel_id)
        return True
    return False