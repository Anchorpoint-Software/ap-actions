from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import sys

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        import is_git_repo as git
        return git.is_git_repo(path)
    except Exception as e:
        print(str(e))
    return False

if __name__ == "__main__":
    ctx = ap.Context.instance()
    ui = ap.UI()
    
    print (sys.path)
    
    settings = aps.Settings("gitsettings")

    dialog = ap.Dialog()
    dialog.icon = ctx.icon
    dialog.title = "Git Settings"

    dialog.show(settings)