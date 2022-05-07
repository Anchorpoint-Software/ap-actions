import anchorpoint as ap
import os
from pathlib import Path

def contains_git_repo(path: str):
    return os.path.exists(os.path.join(path, ".git"))

def on_action_enable(path: str, ctx: ap.Context) -> bool:
    if contains_git_repo(path): return False
    p = Path(path)
    
    while p.parent is not p:
        p = p.parent
        if contains_git_repo(p): return False

    return True