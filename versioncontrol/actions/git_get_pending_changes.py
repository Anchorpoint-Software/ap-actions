import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def print_changes(repo: GitRepository):
    ui.clear_console()
    
    print("Uncommitted Changes")
    print("==================")
    uncommitted = repo.get_pending_changes(staged = False)
    print(uncommitted)

    print("\n\nStaged Changes")
    print("==============")
    staged = repo.get_pending_changes(staged = True)
    print(staged)

    ui.show_console()

repo = GitRepository.load(path)
if repo:
    ctx.run_async(print_changes, repo)