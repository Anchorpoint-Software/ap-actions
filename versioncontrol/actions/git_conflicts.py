from git import GitCommandError
import anchorpoint as ap
import apsync as aps
import git_errors

import sys, os, importlib
script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
from vc.models import ConflictResolveState
from git_lfs_helper import LFSExtensionTracker

from git_timeline import map_commit

if script_dir in sys.path: sys.path.remove(script_dir)

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

def on_vc_resolve_conflicts(channel_id: str, conflict_handling: ap.VCConflictHandling, paths: Optional[list[str]], ctx):
    from vc.apgit.utility import get_repo_path
    
    project_path = ctx.project_path
    path = get_repo_path(channel_id, project_path)
    repo = GitRepository.load(path)
    if not repo:
        return

    is_rebasing = repo.is_rebasing()
    is_merging = repo.is_merging()
    is_conflict_from_stash = not is_rebasing and not is_merging

    if is_rebasing:
        raise "Conflict resolving for Rebasing is not supported yet"

    try:
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
            # When rebasing or applying a stash theirs and ours is inverse
            if conflict_handling == ap.VCConflictHandling.TakeOurs:
                progress = None
                if not paths:
                    progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
                
                if is_conflict_from_stash or is_rebasing:
                    repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)
                else: # Merging 
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)

            elif conflict_handling == ap.VCConflictHandling.TakeTheirs:
                progress = None
                if not paths:
                    progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
                
                if is_conflict_from_stash or is_rebasing:
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)
                else: # Merging
                    repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)

    except Exception as e:
        if not git_errors.handle_error(e):
            raise e
    
    if repo.has_conflicts() == False: 
        try:
            if repo.is_rebasing():
                repo.continue_rebasing()
            elif repo.is_merging():
                repo.continue_merge()
            elif is_conflict_from_stash:
                stash = repo.get_branch_stash()
                if stash:
                    dialog = ap.Dialog()
                    dialog.icon = ":/icons/Misc/shelf.svg"
                    dialog.title = "Shelved Files"
                    dialog.add_text("Anchorpoint has created backup copies of your recent changes. They are called <b>shelved files</b>.<br>Check your project if everything is ok and clear your shelved files afterwards.")
                    dialog.add_info("Learn more about <a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/git/4-Resolving-conflicts/#shelved-files'>Shelved Files</a>")
                    dialog.add_button("Continue", callback=lambda d: d.close())
                    dialog.show()

        except Exception as e:
            if repo.has_conflicts() and repo.is_rebasing():
                # When rebasing, the next commit to rebase can conflict again. This is not an error but OK
                on_vc_resolve_conflicts(channel_id, conflict_handling, None, ctx)
            else:
                raise e
        finally:
            if rebase_head:
                ids_to_delete = [rebase_head]
                ap.delete_timeline_channel_entries(channel_id, ids_to_delete)

def get_lfs_cached_file(sha256, repo_dir):
    import os
    try:
        first_digits = sha256[:2]
        second_digits = sha256[2:4]
        lfs_cache_file = os.path.join(repo_dir, ".git", "lfs", "objects", first_digits, second_digits, sha256)
        
        if not os.path.exists(lfs_cache_file):
            return None
        return lfs_cache_file
    except Exception as e:
        print(f"get_lfs_cached_file exception: {str(e)}")
        return None

def on_vc_load_conflict_details(channel_id: str, file_path: str, ctx):
    path = get_repo_path(channel_id, ctx.project_path)
    repo = GitRepository.load(path)
    if not repo:
        print("Could not load repository")
        return None
    
    if not repo.is_file_conflicting(file_path):
        print("File is not conflicting")
        return None
    
    rel_filepath = os.path.relpath(file_path, path).replace("\\", "/")

    branch_current = repo.get_current_branch_name()
    merge_head_id = repo.get_merge_head()
    branch_incoming = repo.get_branch_name_from_id(merge_head_id)
    is_conflict_from_stash = False

    if repo.is_merging() == False and repo.is_rebasing() == False:
        # When not merging or rebasing, we have conflicts from the stash application
        # Swap entries when conflict is from stash
        branch_incoming = branch_current # Incoming branch is pulled commit aka current branch
        branch_current = None # Branch is None aka not committed
        is_conflict_from_stash = True

    lfsExtensions = LFSExtensionTracker(repo)

    conflict_model = ap.ConflictDetails()
    if branch_current:
        conflict_model.current_branch = branch_current 
    if branch_incoming:
        conflict_model.incoming_branch = branch_incoming
    
    if branch_current:
        conflict_model.current_entry = map_commit(repo, repo.get_last_history_entry_for_file(rel_filepath, branch_current))
    conflict_model.incoming_entry = map_commit(repo, repo.get_last_history_entry_for_file(rel_filepath, branch_incoming))

    if is_conflict_from_stash: 
        status_incoming, status_current = repo.get_file_conflict_status(rel_filepath)
    else:
        status_current, status_incoming = repo.get_file_conflict_status(rel_filepath)
    
    if status_current:
        conflict_model.current_change.status = status_current
    conflict_model.current_change.path = file_path
    
    if status_incoming:
        conflict_model.incoming_change.status = status_incoming
    conflict_model.incoming_change.path = file_path

    if lfsExtensions.is_file_tracked(file_path):
        # Ref where the file still existed
        lfs_ref_current = conflict_model.current_entry.id if not is_conflict_from_stash else None
        lfs_ref_incoming = conflict_model.incoming_entry.id
        if status_current == ap.VCFileStatus.Deleted and not is_conflict_from_stash:
            lfs_ref_current = lfs_ref_current + "^"
        if status_incoming == ap.VCFileStatus.Deleted:
            lfs_ref_incoming = lfs_ref_incoming + "^"

        conflict_model.is_text = False
        if is_conflict_from_stash:
            stash = repo.get_branch_stash()
            if stash:
                stash_id = f"stash@{{{stash.id}}}"
                hash_current = repo.get_lfs_filehash([rel_filepath], stash_id)
            else:
                hash_current = []
        else:
            hash_current = repo.get_lfs_filehash([rel_filepath], lfs_ref_current)

        hash_incoming = repo.get_lfs_filehash([rel_filepath], lfs_ref_incoming)
        conflict_model.current_change.cached_path = None if len(hash_current) == 0 else get_lfs_cached_file(hash_current[rel_filepath], path)
        conflict_model.incoming_change.cached_path = None if len(hash_incoming) == 0 else get_lfs_cached_file(hash_incoming[rel_filepath], path)
    else:
        conflict_model.is_text = True
    
    return conflict_model