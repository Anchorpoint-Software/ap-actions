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
        cancel_rebase(channel_id, project_path)
    elif conflict_handling == ap.VCConflictHandling.TakeOurs:
        # git checkout --theirs (theirs and ours is inverse when rebasing)
        repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)
    elif conflict_handling == ap.VCConflictHandling.TakeTheirs:
        # git checkout --ours (theirs and ours is inverse when rebasing)
        repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)
    elif conflict_handling == ap.VCConflictHandling.External:
        repo.launch_external_merge("vscode", paths)    
    
    if repo.has_conflicts() == False:
        repo.continue_rebasing()

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id == "gitcancelrebase":
        ctx.run_async(cancel_rebase, channel_id, ctx.project_path)
    if action_id == "gitresolveconflicts": 
        ctx.run_async(resolve_conflicts, channel_id)