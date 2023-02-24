from git import GitCommandError
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os, importlib
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.models import ConflictResolveState
sys.path.remove(script_dir)

def cancel_merge(channel_id, project_path):
    from vc.apgit.utility import get_repo_path
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo:
        return

    try:
        if repo.is_rebasing():
            repo.abort_rebasing()
        elif repo.is_merging():
            repo.abort_merge()
    except Exception as e:
        if not git_errors.handle_error(e):
            raise e

    ap.refresh_timeline_channel(channel_id)

def create_merge_commit(repo: GitRepository, with_conflicts: bool):
    if with_conflicts:
        repo.commit(f"Merge remote changes into {repo.get_current_branch_name()} with resolved conflicts")
    else:
        repo.commit(f"Merge remote changes into {repo.get_current_branch_name()}")

def on_vc_resolve_conflicts(channel_id: str, conflict_handling: ap.VCConflictHandling, paths: Optional[list[str]], ctx):
    from vc.apgit.utility import get_repo_path
    
    project_path = ctx.project_path
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo:
        return

    try:
        is_rebasing = repo.is_rebasing()
        is_merging = repo.is_merging()
        if is_rebasing:
            rebase_head = repo.get_rebase_head()
        else: 
            rebase_head = None

        if conflict_handling == ap.VCConflictHandling.Cancel:
            progress = ap.Progress("Canceling", show_loading_screen=True)
            cancel_merge(channel_id, project_path)
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
                
                if is_merging:
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)
                else:
                    repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)

            elif conflict_handling == ap.VCConflictHandling.TakeTheirs:
                progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
                
                # git checkout --ours (theirs and ours is inverse when rebasing)
                if len(unstaged_files) > 0:
                    repo.remove_files(unstaged_files)

                if is_merging:
                    repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)
                else:
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)

    except Exception as e:
        if not git_errors.handle_error(e):
            raise e
    
    if repo.has_conflicts() == False: 
        try:
            if repo.is_rebasing():
                repo.continue_rebasing()
            elif repo.is_merging():
                create_merge_commit(repo, True)
                # repo.continue_merge() # This will create a merge commit with the Git default commit message
        except Exception as e:
            if repo.has_conflicts():
                # When rebasing, the next commit to rebase can conflict again. This is not an error but OK
                on_vc_resolve_conflicts(channel_id, conflict_handling, None, ctx)
            else:
                raise e
        finally:
            if rebase_head:
                ids_to_delete = [rebase_head]
                ap.delete_timeline_channel_entries(channel_id, ids_to_delete)