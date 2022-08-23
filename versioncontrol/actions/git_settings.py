from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import sys, os

script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(script_dir)

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        import is_git_repo as git
        return git.is_git_repo(path)
    except Exception as e:
        print(str(e))
    return False

def prune():
    ui = ap.UI()
    repo_path = get_repo_path("Git", project_path)
    repo = GitRepository.load(repo_path)
    if not repo: return

    progress = ap.Progress("Clearing Cache")
    count = repo.prune_lfs()
    if count == 0: 
        ui.show_info("Cache is already cleared")
    else:
        ui.show_info(f"Cleared {count} objects")

def prune_pressed(dialog):
    dialog.close()
    ctx.run_async(prune)
    

if __name__ == "__main__":
    ctx = ap.Context.instance()
    project_path = ctx.project_path

    settings = aps.Settings("gitsettings")

    dialog = ap.Dialog()
    dialog.icon = ctx.icon
    dialog.title = "Git Settings"

    dialog.add_button("Clear Cache", callback=prune_pressed)
    dialog.add_info("Removes local files from the Git LFS cache that are old. This will never delete <br>any data on the server or data that is not pushed to a Git remote.")

    dialog.show(settings)