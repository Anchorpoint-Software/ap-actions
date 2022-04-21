import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def stage_files(repo: GitRepository, files: list[str]):
    repo.stage_files(files)
    ui.show_success("Files Staged")

repo = GitRepository.load(path)
if repo:
    ctx.run_async(stage_files, repo, ctx.selected_files)
