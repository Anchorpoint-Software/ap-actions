from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import sys, os, pathlib

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        import is_git_repo as git
        return git.is_git_repo(path)
    except Exception as e:
        print(str(e))
    return False

def open_terminal_pressed(dialog):
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))
    from vc.apgit.repository import GitRepository
    from vc.apgit_utility.install_git import get_git_cmd_path
    import platform

    env = GitRepository.get_git_environment()
    for key,value in env.items():
        os.putenv(key, value)

    ctx = ap.get_context()
    if platform.system() == "Darwin":
        def get_osascript():
            gitdir = os.path.dirname(get_git_cmd_path())
            return (
                f"if application \"Terminal\" is running then\n"
                f"\ttell application \"Terminal\"\n"
                f"\t\tdo script \"cd \\\"{ctx.project_path}\\\" && export PATH=\\\"{gitdir}\\\":$PATH\"\n"
                f"\t\tactivate\n"
                f"\tend tell\n"
                f"else\n"
                f"\ttell application \"Terminal\"\n"
                f"\t\tdo script \"cd \\\"{ctx.project_path}\\\" && export PATH=\\\"{gitdir}\\\":$PATH\" in window 1\n"
                f"\t\tactivate\n"
                f"\tend tell\n"
                f"end if\n"
            )
        
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            with open(tmp.name, "w") as f:
                f.write(get_osascript())
        finally:
            os.system(f"osascript \"{tmp.name}\"")
            os.remove(tmp.name)

    elif platform.system() == "Windows":
        path = os.environ["PATH"]
        os.putenv("PATH", f"{os.path.dirname(get_git_cmd_path())};{path}")
        os.system(f"start cmd /k \"{pathlib.Path(ctx.project_path).drive} & cd {ctx.project_path}\"")

    dialog.close()

if __name__ == "__main__":
    script_dir = os.path.join(os.path.dirname(__file__), "..")
    sys.path.insert(0, script_dir)

    from vc.apgit.repository import * 
    from vc.apgit.utility import get_repo_path
    if script_dir in sys.path: sys.path.remove(script_dir)

    ctx = ap.get_context()
    project_path = ctx.project_path

    settings = aps.Settings("gitsettings")

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

    dialog = ap.Dialog()
    dialog.icon = ctx.icon
    dialog.title = "Git Commands"

    dialog.add_button("Open Git Console / Terminal", callback=open_terminal_pressed, primary=False)
    dialog.add_info("Opens the Terminal / Command line with a set up git environment.<br>Can be used to run git commands on this computer.")
    dialog.add_empty()

    dialog.add_button("Clear Cache", callback=prune_pressed, primary=False)
    dialog.add_info("Removes local files from the Git LFS cache that are old. This will never delete <br>any data on the server or data that is not pushed to a Git remote.")

    dialog.show(settings)