from typing import Optional
import os

script_dir = os.path.join(os.path.dirname(__file__), "..")

def extract_conflicting_files(diff_file):
    import re
    try:        
        # Extract SHA256 values
        sha256_values = re.findall(r'oid sha256:([a-f0-9]+)', diff_file)
        print(sha256_values)
        sha256_current = sha256_values[0]
        sha256_incoming = sha256_values[1]

        # Extract branch names
        branch_current = re.findall(r'<<<<<<< (\w+)', diff_file)[0]
        branch_incoming = re.findall(r'>>>>>>> (\w+)', diff_file)[0]

        return branch_current, sha256_current, branch_incoming, sha256_incoming
        
    except Exception as e:
        print(f"extract_conflicting_files exception: {str(e)}")
        return None

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

def fetch_lfs_file(file, branch, repo, progress = None):
    repo.fetch_lfs_files([branch], [file], progress)
    pass

def on_vc_load_files(channel_id: str, filepaths: list[str], ref: Optional[str], ctx):
    import sys
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_repo_path
    if script_dir in sys.path: sys.path.remove(script_dir)

    path = get_repo_path(channel_id, ctx.project_path)
    repo = GitRepository.load(path)
    if not repo:
        return
    
    files = {}
    for filepath in filepaths:
        rel_filepath = os.path.relpath(filepath, path)
        hash_result = repo.get_lfs_filehash(rel_filepath, ref)
        if len(hash_result) == 0:
            files[filepath] = None
            
        cached_file = get_lfs_cached_file(hash, path)
        if cached_file:
            print(f"File {filepath} is already cached")
            files[filepath] = cached_file
        else:
            print(f"File {filepath} is not cached")
            repo.fetch_lfs_files([ref] if ref else None, [rel_filepath], None)
            cached_file = get_lfs_cached_file(hash, path)
            if cached_file:
                print(f"File {filepath} is now cached")
                files[filepath] = cached_file
            else:
                print(f"Could not cache File {filepath}")
                files[filepath] = None
            
    return files