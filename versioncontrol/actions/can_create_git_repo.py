import anchorpoint as ap
from pathlib import Path
import os, sys

try:

    sys.path.insert(0, os.path.split(__file__)[0])
    import is_git_repo as git
except Exception as e:
    print(str(e))

def on_is_action_enabled(path: str, ctx: ap.Context) -> bool:
    return git.is_git_repo(path)