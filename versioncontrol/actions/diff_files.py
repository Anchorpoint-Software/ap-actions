import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

is_file_action = ctx.type == ap.Type.File
files = ctx.selected_files

def diff():
    repo = GitRepository.load(path)
    if repo:
        if is_file_action:
            repo.launch_external_diff("vscode", files)
        else:
            repo.launch_external_diff("vscode")
diff()