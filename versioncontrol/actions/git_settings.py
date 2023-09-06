import anchorpoint as ap
import apsync as aps
import os, sys, pathlib, platform

current_dir = os.path.dirname(__file__)
script_dir = os.path.join(os.path.dirname(__file__), "..")

def refresh_timeline(dialog):
    dialog.store_settings()
    ap.vc_load_pending_changes("Git", False)

class GitAccountSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.dialog = ap.Dialog()
        self.dialog.add_switch(True, var="autopush", text="Combine Commit and Push", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will automatically push your changes to the remote Git repository")
        self.dialog.add_switch(True, var="autolock", text="Automatically lock changed files", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will lock all binaries that have been modified. Locks will be released when the commits are pushed to the remote Git repository. <br><a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/projects/5-File-locking/#git-projects'>Learn about File Locking</a>")
        self.dialog.add_switch(True, var="notifications", text="Show notifications for new commits")
        self.dialog.add_info("Show a system notification when new commits are available on the remote Git repository")
        self.dialog.load_settings(self.get_settings())


    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitSettings")
    
    def auto_push_enabled(self):
        return self.get_settings().get("autopush", True)
    
    def auto_lock_enabled(self):
        return self.get_settings().get("autolock", True)
    
    def notifications_enabled(self):
        return self.get_settings().get("notifications", True)

def apply_git_url(dialog, ctx, repo_path):
    sys.path.insert(0, current_dir)
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    if current_dir in sys.path: sys.path.remove(current_dir)
    if script_dir in sys.path: sys.path.remove(script_dir)
     
    url = dialog.get_value("url")
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project:
        ap.UI().show_error("Could not change URL", "The project could not be loaded")
        return
    
    channel = aps.get_timeline_channel(project, "Git")
    if not channel:
        ap.UI().show_error("Could not change URL", "The Git channel could not be loaded")
        return

    metadata = channel.metadata
    old_url = metadata["gitRemoteUrl"]
    metadata["gitRemoteUrl"] = url
    channel.metadata = metadata

    try:
        aps.update_timeline_channel(project, channel)

        repo = GitRepository.load(repo_path)
        repo.update_remote_url(url)

        ap.UI().show_success("Url changed")
    except:
        metadata["gitRemoteUrl"] = old_url
        channel.metadata = metadata
        aps.update_timeline_channel(project, channel)
        ap.UI().show_error("Could not change URL", "The URL could not be changed")

def open_terminal_pressed(dialog): 
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    from vc.apgit_utility.install_git import get_git_cmd_path
    if script_dir in sys.path: sys.path.remove(script_dir)

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

def prune(project_path):
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_repo_path
    if script_dir in sys.path: sys.path.remove(script_dir)

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

def prune_pressed(ctx: ap.Context):
    ctx.run_async(prune, ctx.project_path)

class GitProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        sys.path.insert(0, current_dir)
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path
        if current_dir in sys.path: sys.path.remove(current_dir)
        if script_dir in sys.path: sys.path.remove(script_dir)

        if ctx.project_id is None:
            raise("GitProjectSettings can only be used in the context of a project")

        self.ctx = ctx
        self.dialog = ap.Dialog()

        path = get_repo_path("Git", ctx.project_path)
        repo = GitRepository.load(path)
        if repo:
            url = repo.get_remote_url()

            self.dialog.add_text("Repository URL")
            self.dialog.add_input(url if url else "", var="url", width=400)
            self.dialog.add_info("This changes the remote URL of your Git repository, use with caution")
            self.dialog.add_button("Apply", callback=lambda d: apply_git_url(d, self.ctx, path))

            self.dialog.add_empty()
            self.dialog.add_button("Open Git Console / Terminal", callback=open_terminal_pressed, primary=False)
            self.dialog.add_info("Opens the Terminal / Command line with a set up git environment.<br>Can be used to run git commands on this computer.")
            self.dialog.add_empty()

            self.dialog.add_button("Clear Cache", callback=lambda d: prune_pressed(ctx), primary=False)
            self.dialog.add_info("Removes local files from the Git LFS cache that are old. This will never delete <br>any data on the server or data that is not pushed to a Git remote.")
            self.dialog.add_empty()

            self.dialog.add_switch(True, var="gitkeep", text="Create .gitkeep files in empty folders", callback=lambda d,v: d.store_settings())
            self.dialog.add_info("Git does not track empty folders. Anchorpoint will create a hidden <i>.gitkeep</i> file<br>in new folders to make sure they are tracked by Git.")

            self.dialog.load_settings(self.get_settings())

    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitProjectSettings", self.ctx.project_id)
    
    def gitkeep_enabled(self):
        return self.get_settings().get("gitkeep", True)


def on_show_account_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitAccountSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)

def on_show_project_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitProjectSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)