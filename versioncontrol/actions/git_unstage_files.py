import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def unstage_files(repo: GitRepository, files: list[str]):
    repo = GitRepository.load(path)
    if repo is None: return
    repo.unstage_files(files)
    ui.show_success("Files Unstaged")

ctx.run_async(unstage_files, ctx.selected_files)
