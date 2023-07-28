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

            # When rebasing theirs and ours is inverse
            # When merging, ours is current working directory and theirs is merging changes
            # When applying a stash, theirs are the changes from the stash
            unstaged_files, staged_files = repo.get_deleted_files()
            if conflict_handling == ap.VCConflictHandling.TakeOurs:
                progress = None
                if not paths:
                    progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
                
                if not is_merging or is_rebasing:
                    if len(staged_files) > 0:
                        try:
                            repo.remove_files(staged_files)
                        except Exception as e:
                            print("Could not call git rm, ignored: " + str(e))
                            pass
                    repo.conflict_resolved(ConflictResolveState.TAKE_THEIRS, paths)
                else: # Merging 
                    if len(unstaged_files) > 0:
                        try:
                            repo.remove_files(unstaged_files)
                        except Exception as e:
                            print("Could not call git rm, ignored: " + str(e))
                            pass
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)

            elif conflict_handling == ap.VCConflictHandling.TakeTheirs:
                progress = None
                if not paths:
                    progress = ap.Progress("Resolving Conflicts", show_loading_screen=True)
                
                if not is_merging or is_rebasing:
                    if len(unstaged_files) > 0:
                        try:
                            repo.remove_files(unstaged_files)
                        except Exception as e:
                            print("Could not call git rm, ignored: " + str(e))
                            pass
                    repo.conflict_resolved(ConflictResolveState.TAKE_OURS, paths)
                else: # Merging
                    if len(staged_files) > 0:
                        try:
                            repo.remove_files(staged_files)
                        except Exception as e:
                            print("Could not call git rm, ignored: " + str(e))
                            pass
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

def load_file_content(path):
    import os
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read() 

def is_conflicting_pointer_file(file_content):
    import re
    try:
        pattern = r'^version\s+https:\/\/git-lfs\.github\.com\/spec\/v1\n<<<<<<<\s+\w+\noid\s+sha256:[a-f0-9]+\nsize\s+\d+\n=======\noid\s+sha256:[a-f0-9]+\nsize\s+\d+\n>>>>>>>\s+\w+'
        match = re.match(pattern, file_content)
        return match is not None
    except Exception as e:
        print(f"is_conflicting_pointer_file exception: {str(e)}")
        return False
    
def extract_conflicting_branches(file_content):
    import re
    branch_current = re.findall(r'<<<<<<< (\w+)', file_content)[0]
    branch_incoming = re.findall(r'>>>>>>> (\w+)', file_content)[0]
    return branch_current, branch_incoming

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
    
    content = load_file_content(file_path)
    if not content:
        print("Could not load file content")
        return None
    
    rel_filepath = os.path.relpath(file_path, path)
    branch_current, branch_incoming = extract_conflicting_branches(content)

    if branch_current == "HEAD":
        branch_current = repo.get_current_branch_name()

    conflict_model = ap.ConflictDetails()
    conflict_model.current_branch = branch_current
    conflict_model.incoming_branch = branch_incoming
    conflict_model.current_entry = map_commit(repo.get_last_history_entry_for_file(rel_filepath, branch_current))
    conflict_model.incoming_entry = map_commit(repo.get_last_history_entry_for_file(rel_filepath, branch_incoming))

    status_current, status_incoming = repo.get_file_status(rel_filepath)
    
    if status_current:
        conflict_model.current_change.status = status_current
    conflict_model.current_change.path = file_path
    
    if status_incoming:
        conflict_model.incoming_change.status = status_incoming
    conflict_model.incoming_change.path = file_path

    if is_conflicting_pointer_file(content):
        conflict_model.is_text = False
        hash_current = repo.get_lfs_filehash([rel_filepath], branch_current)
        hash_incoming = repo.get_lfs_filehash([rel_filepath], branch_incoming)
        conflict_model.current_change.cached_path = None if len(hash_current) == 0 else get_lfs_cached_file(hash_current[rel_filepath], path)
        conflict_model.incoming_change.cached_path = None if len(hash_incoming) == 0 else get_lfs_cached_file(hash_incoming[rel_filepath], path)
    else:
        conflict_model.is_text = True
        conflict_model.file_current = None
        conflict_model.file_incoming = None
    
    return conflict_model