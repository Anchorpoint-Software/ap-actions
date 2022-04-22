from git import GitCommandError
import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def resolve_conflicts_async():
    repo = GitRepository.load(path)
    if repo == None: return

    if repo.has_conflicts() == False:
        ui.show_info("Nothing to merge")
        return 

    if repo.is_rebasing() == False:
        ui.show_error("Not Rebasing", "Merge handling is not implemented, only rebase")
        return

    try:
        repo.launch_external_merge("vscode")
        if repo.has_conflicts():
            ui.show_info("Repo still contains conflicts")
            return
        
        repo.continue_rebasing()

    except GitCommandError as e:
        ui.show_error("Failed to resolve conflicts in Git Repository", e.stderr, 10000)

ctx.run_async(resolve_conflicts_async)