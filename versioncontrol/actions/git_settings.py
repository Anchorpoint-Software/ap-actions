import anchorpoint as ap
import apsync as aps
import os, sys, pathlib, platform, webbrowser

current_dir = os.path.dirname(__file__)
script_dir = os.path.join(os.path.dirname(__file__), "..")

from git_errors import handle_error

def refresh_timeline(dialog):
    dialog.store_settings()
    ap.vc_load_pending_changes("Git", False)

class GitAccountSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.dialog = ap.Dialog()
        self.dialog.add_switch(True, var="autopush", text="Combine Commit and Push", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will automatically push your changes to the remote Git repository.")
        self.dialog.add_switch(True, var="autolock", text="Automatically lock changed files", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will lock all binaries that have been modified. Locks will be released when the commits are pushed to the remote Git repository. <br><a href='https://docs.anchorpoint.app/docs/general/workspaces-and-projects/file-locking/#git-projects'>Learn about File Locking</a>.")
        self.dialog.add_switch(True, var="notifications", text="Show notifications for new commits")
        self.dialog.add_info("Show a system notification when new commits are available on the remote Git repository.")
        
        self.dialog.add_text("Clear Git file cache automatically:\t").add_dropdown("Files older than one week", ["Always", "Files older than one week", "Never"], var="autoprune")
        self.dialog.add_info("Clears the Git LFS cache after each push and pull to save disk space. This will never delete any data on the server or data that is not pushed to a Git remote.")
        
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
    
    def auto_prune_days(self):
        autoprune = self.get_settings().get("autoprune")
        if autoprune == "Always":
            return 0
        elif autoprune == "Never":
            return -1
        else:
            return 7

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
    if "gitRemoteUrl" in metadata:
        old_url = metadata["gitRemoteUrl"]
    else: 
        old_url = None
    metadata["gitRemoteUrl"] = url
    channel.metadata = metadata

    try:
        aps.update_timeline_channel(project, channel)
        repo = GitRepository.load(repo_path)
        repo.update_remote_url(url)
        ap.reload_timeline_entries()

        ap.UI().show_success("Url changed")
        print(f"Git repository URL was changed by user from {old_url} to {url}")
    except Exception as e:
        metadata["gitRemoteUrl"] = old_url
        channel.metadata = metadata
        aps.update_timeline_channel(project, channel)

        error_message = str(e)
        if "fatal: repository" in error_message and "not found" in error_message:
            ap.UI().show_error("Could not change URL", "The repository could not be found, did you mistype the URL?")
        elif not handle_error(e, repo_path):
            ap.UI().show_error("Could not change URL", str(e))
    finally:
        dialog.set_processing("applyurl", False)

def apply_git_url_async(dialog, ctx, repo_path):
    dialog.set_processing("applyurl", True, "Changing URL")
    ctx.run_async(apply_git_url, dialog, ctx, repo_path)

def reapply_sparse_checkout(dialog, ctx: ap.Context, repo_path):
    from vc.apgit.repository import GitRepository
    try:
        repo = GitRepository.load(repo_path)
        repo.sparse_reapply()

        ap.UI().show_success("Sparse Checkout refreshed")
    except Exception as e:
        ap.UI().show_error("Could not refresh sparse checkout", str(e))
    finally:
        dialog.set_processing("reapplysparse", False)

def reapply_sparse_checkout_async(dialog, ctx: ap.Context, repo_path):
    dialog.set_processing("reapplysparse", True, "Refreshing Sparse Checkout")
    ctx.run_async(reapply_sparse_checkout, dialog, ctx, repo_path)

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
        if os.path.exists(ctx.project_path):
            os.system(f"start cmd /k \"{pathlib.Path(ctx.project_path).drive} & cd {ctx.project_path}\"")
        else:
            os.system(f"start cmd /k")

def prune(dialog, project_path):
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    from vc.apgit.utility import get_repo_path
    if script_dir in sys.path: sys.path.remove(script_dir)

    ui = ap.UI()
    repo_path = get_repo_path("Git", project_path)
    repo = GitRepository.load(repo_path)
    if not repo: return

    progress = ap.Progress("Clearing Cache")
    dialog.set_processing("prune_lfs", True, "Clearing Cache")
    count = repo.prune_lfs(force=True)
    dialog.set_processing("prune_lfs", False)
    if count == 0: 
        ui.show_info("Cache is already cleared")
    else:
        ui.show_info(f"Cleared {count} objects")

def prune_pressed(dialog, ctx: ap.Context):
    ctx.run_async(prune, dialog, ctx.project_path)

def clear_credentials_async(dialog, repo_path, url):
    if not url:
        ap.UI().show_error("Could not clear credentials", "No URL is set up")
        return
    try:
        dialog.set_processing("updatecreds", True, "Updating")
        sys.path.insert(0, current_dir)
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        if current_dir in sys.path: sys.path.remove(current_dir)
        if script_dir in sys.path: sys.path.remove(script_dir)
        
        try:
            repo = GitRepository.load(repo_path)
        except:
            repo = None

        try:
            if repo and repo.clear_credentials():
                repo.fetch()
                ap.UI().show_success("Credentials updated")
            else:
                host, path = GitRepository.get_git_url_info(url)
                GitRepository.erase_credentials(host, "https", path if "azure" in host else None)
                ap.UI().show_success("Credentials cleared")
        except Exception as e:
            print(e)
            ap.UI().show_error("Could not clear credentials")
    finally:
        dialog.set_processing("updatecreds", False)

def update_credentials_pressed(dialog, ctx: ap.Context, repo_path, url):
    ctx.run_async(clear_credentials_async, dialog, repo_path, url)

def store_shared_setting(key, value, settings):
    settings.set(key, value)
    settings.store()

def open_repository_on_web(dialog: ap.Dialog):
        url = dialog.get_value("url")
        webbrowser.open(url, new=0, autoraise=True)

class GitProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        sys.path.insert(0, current_dir)
        sys.path.insert(0, script_dir)
        from vc.apgit.repository import GitRepository
        from vc.apgit.utility import get_repo_path, get_repo_url_from_channel
        if current_dir in sys.path: sys.path.remove(current_dir)
        if script_dir in sys.path: sys.path.remove(script_dir)

        if ctx.project_id is None:
            raise("GitProjectSettings can only be used in the context of a project")

        self.ctx = ctx
        self.dialog = ap.Dialog()

        path = get_repo_path("Git", ctx.project_path)
        try:
            repo = GitRepository.load(path)
            self.repo_available = True
            url = repo.get_remote_url() if repo else None
        except:
            repo = None
            self.repo_available = False
            url = get_repo_url_from_channel("Git", ctx.workspace_id, ctx.project_id)

        self.dialog.add_text("<b>Repository URL</b>")
        self.dialog.add_input(url if url != None else "", var="url", width=400).add_button("Visit",var="visit",callback = open_repository_on_web, primary=False)
        self.dialog.add_info("This changes the remote URL of your Git repository, use with caution")
        self.dialog.add_button("Apply URL", var="applyurl", callback=lambda d: apply_git_url_async(d, self.ctx, path), primary=False)
        self.dialog.add_empty()

        self.dialog.add_switch(True, var="gitkeep", text="Create .gitkeep files in new folders", callback=lambda d,v: d.store_settings())
        self.dialog.add_info("Anchorpoint adds <i>.gitkeep</i> files to support empty folders in Git.")

        self.dialog.add_switch(True, var="autolfs", text="Automatically track all binary files as LFS files", callback=lambda d,v: store_shared_setting("autolfs", v, self.get_shared_settings()))
        self.dialog.add_info("Disable this to manually configure Git LFS for files using a <i>.gitattributes</i> file.")
        self.dialog.add_empty()

        self.dialog.add_text("<b>Auto Lock Files</b>")
        self.dialog.add_tag_input(["unity"], "txt", var="lockextensions", width=400, callback=lambda d,v: store_shared_setting("lockextensions", v, self.get_shared_settings()))
        self.dialog.add_info("Anchorpoint automatically locks binary files. Add text files for automatic locking.")
        self.dialog.add_empty()

        self.dialog.add_text("<b>Git Commands</b>")
        
        self.dialog.add_button("Open Git Console / Terminal", callback=open_terminal_pressed, primary=False)
        self.dialog.add_info("Opens the Terminal / Command line with a set up Git environment.<br>Can be used to run Git commands on this computer.")

        self.dialog.add_button("Clear Cache", var="prune_lfs", callback=lambda d: prune_pressed(d, ctx), primary=False, enabled=self.repo_available)
        self.dialog.add_info("Removes local files from the Git LFS cache that are old. This will never delete <br>any data on the server or data that is not pushed to a Git remote.")

        self.dialog.add_button("Update Credentials" if repo else "Clear Credentials", var="updatecreds", callback=lambda d: update_credentials_pressed(d, ctx, path, url), primary=False)
        if repo:
            self.dialog.add_info("This will show you the login dialog again to update your credentials.")
        else:
            self.dialog.add_info("This will clear your credentials for your configured Git remote (e.g. Azure DevOps).")

        self.dialog.load_settings(self.get_settings())
        shared_settings = self.get_shared_settings()
        self.dialog.set_value("lockextensions", shared_settings.get("lockextensions", ["unity"]))
        self.dialog.set_value("autolfs", shared_settings.get("autolfs", True))

        if self.repo_available and repo.is_sparse_checkout_enabled():
            self.dialog.add_empty()
            self.dialog.add_text("<b>Fix Issues</b>")
            self.dialog.add_button("Refresh Sparse Checkout", var="reapplysparse", callback=lambda d: reapply_sparse_checkout_async(d, self.ctx, path), primary=False)
            self.dialog.add_info("Repairs the state of Unloaded/Downloaded folders if they don't show<br>the correct content. This may have happened after resolving conflicts.")


    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitProjectSettings", self.ctx.project_id)
    
    def get_shared_settings(self):
        return aps.SharedSettings(self.ctx.project_id, self.ctx.workspace_id, "GitProjectSettings")
    
    def gitkeep_enabled(self):
        if not self.repo_available:
            return False
        return self.get_settings().get("gitkeep", True)

    def lfsautotrack_enabled(self):
        return self.get_shared_settings().get("autolfs", True)
    
    def get_lock_extensions(self):
        return self.get_shared_settings().get("lockextensions", [])

def on_show_account_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitAccountSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)

def on_show_project_preferences(settings_list, ctx: ap.Context):
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project: return
    channel = aps.get_timeline_channel(project, "Git")
    if not channel: return

    gitSettings = GitProjectSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)