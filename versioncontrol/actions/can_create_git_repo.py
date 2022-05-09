import anchorpoint as ap
from pathlib import Path
import os, sys

sys.path.insert(0, os.path.split(__file__)[0])
import is_git_repo as git

def on_action_enable(path: str, ctx: ap.Context) -> bool:
    return git.is_git_repo(path)