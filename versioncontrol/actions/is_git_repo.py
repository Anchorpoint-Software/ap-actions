import os
from pathlib import Path
import anchorpoint as ap

def path_contains_git_repo(path: str) -> bool:
    return os.path.exists(os.path.join(path, ".git"))

def is_git_repo(path: str) -> bool:
    if path_contains_git_repo(path): return True
    p = Path(path)
    while p.parent != p:
        p = p.parent
        if path_contains_git_repo(p): return True

    return False

def on_is_action_enabled(path: str, ctx: ap.Context) -> bool:
    return is_git_repo(path)