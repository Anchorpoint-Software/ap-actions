import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()

try:
    from vc.apgit.repository import * 
except Warning as e:
    sys.exit(0)

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def create_repo(dialog: ap.Dialog):
    name = dialog.get_value("name")
    repo_path = os.path.join(path, name)
    if GitRepository.is_repo(repo_path):
        ui.show_info("Already a Git repo")
    else:
        repo = GitRepository.create(repo_path)
        ui.navigate_to_folder(repo_path)
        ui.show_success("Git Repository Initialized")
        dialog.close()

dialog = ap.Dialog()
dialog.title = "Create a Git repository"
dialog.icon = ctx.icon
dialog.add_input(placeholder="Repository Name", var="name")
dialog.add_button("Create", callback=create_repo)
dialog.show()