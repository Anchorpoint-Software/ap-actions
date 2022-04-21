import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def commit_async(repo: GitRepository, message: str):
    try:
        repo.commit(message)
        ui.show_success("Commit succeeded")
    except Exception as e:
        ui.show_error("Commit Failed", e)

repo = GitRepository.load(path)

def commit(dialog: ap.Dialog):
    ctx.run_async(commit_async, repo, dialog.get_value("message"))
    dialog.close()

if repo:
    staged = repo.get_pending_changes(staged=True)
    changecount = staged.size()
    if changecount == 0:
        ui.show_info("Nothing to commit", "Stage your changes first")
        sys.exit(0)

    dialog = ap.Dialog()
    dialog.title = "Commit"
    dialog.icon = ctx.icon
    dialog.add_input(f"Changed {changecount} files", var="message")
    dialog.add_button("Commit", callback=commit)
    dialog.show()