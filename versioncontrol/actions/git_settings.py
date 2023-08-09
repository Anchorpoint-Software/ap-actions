import anchorpoint as ap
import apsync as aps
import os, sys

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
            self.dialog.load_settings(self.get_settings())

    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitProjectSettings", self.ctx.project_id)


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