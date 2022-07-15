import anchorpoint as ap
import apsync as aps

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        if type != ap.Type.JoinProjectFiles: return False
        project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
        if not project: return False
        channel = aps.get_timeline_channel(project, "Git")
        return channel is not None
    except Exception as e:
        return False

if __name__ == "__main__":
    import sys, os, importlib
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

    importlib.invalidate_caches()

    try:
        from vc.apgit.repository import * 
    except Warning as e:
        sys.exit(0)

    import platform
    import git_repository_helper as helper

    ctx = ap.Context.instance()
    ui = ap.UI()

    project_id = ctx.project_id
    workspace_id = ctx.workspace_id
    project = aps.get_project_by_id(project_id, workspace_id)
    if not project:
        ui.show_error("Cannot create git repository", "You must create a project first")
        sys.exit(0) 

    timeline_channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
    is_join = ctx.type == ap.Type.JoinProjectFiles
    settings = aps.Settings("git_repository")
    class CloneProgress(Progress):
        def __init__(self, progress: ap.Progress) -> None:
            super().__init__()
            self.ap_progress = progress

        def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
            if operation_code == "downloading":
                if info_text:
                    self.ap_progress.set_text(f"Downloading Files: {info_text}")
                else:
                    self.ap_progress.set_text("Downloading Files")
                self.ap_progress.report_progress(current_count / max_count)
            elif operation_code == "updating":
                self.ap_progress.set_text("Updating Files")
                self.ap_progress.report_progress(current_count / max_count)
            else:
                self.ap_progress.set_text("Talking to Server")
                self.ap_progress.stop_progress()
                

    def url_gcm_supported(url: str):
        gcm_supported_providers = ["github", "gitlab", "azure"]
        return any(provider in url for provider in gcm_supported_providers)

    def create_repo(dialog: ap.Dialog):
        location = dialog.get_value("location")
        repo_path = location
        if GitRepository.is_repo(repo_path):
            ui.show_info("Already a Git repo")
        else:
            repo = GitRepository.create(repo_path)
            helper.update_project(repo_path, None, is_join, timeline_channel, project)
            repo.ignore(".ap/project.json", local_only=True)
            ui.show_success("Git Repository Initialized")
            dialog.close()

    def clone_repo_async(repo_path: str, url: str):
        try:
            progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
            repo = GitRepository.clone(url, repo_path, progress=CloneProgress(progress))
            progress.finish()
            helper.update_project(repo_path, url, is_join, timeline_channel, project)
            repo.ignore(".ap/project.json", local_only=True)
            ui.show_success("Git Repository Cloned")
        except Exception as e:
            ui.show_error("Could not add Git Repository", "You might have entered a wrong username / password, or you don't have access to the repository.")

    def clone_repo(dialog: ap.Dialog):
        location = dialog.get_value("location")
        url = dialog.get_value("url")
        repo_path = location
        with os.scandir(repo_path) as it:
            if any(it):
                ui.show_info("Cannot Join Git repository", "Folder must be empty")
                return
        
        dialog.close()
        ctx.run_async(clone_repo_async, repo_path, url)

    def update_dialog(dialog: ap.Dialog, value):
        url = dialog.get_value("url")
        location = dialog.get_value("location")
        remote_enabled = dialog.get_value("remote")
        hide_remote_settings = not remote_enabled

        dialog.hide_row("repotext", hide_remote_settings)
        dialog.hide_row("url", hide_remote_settings)
        
        dialog.hide_row("join", hide_remote_settings)
        dialog.hide_row("create", remote_enabled)

        enable = len(location) > 0
        if not hide_remote_settings:
            enable = enable and len(url) > 0

        dialog.set_enabled("join", enable)
        dialog.set_enabled("create", enable)

        settings.set("browse_path", location)
        settings.store()

    remote_enabled = True
    remote_toggleable = not timeline_channel or "gitRemoteUrl" not in timeline_channel.metadata
    if not remote_toggleable:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
    else:
        remote_url = ""

    hide_remote_settings = not remote_enabled

    dialog = ap.Dialog()
    dialog.title = "Git repository"
    dialog.icon = ctx.icon

    dialog.add_text("<b>Project Folder</b>")
    if platform.system() == "Windows":
        dialog.add_input(placeholder="D:/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)
    else:
        dialog.add_input(placeholder="/users/johndoe/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)

    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)

    dialog.add_switch(remote_enabled, var="remote", callback=update_dialog).add_text("Remote Repository").hide_row(hide=not remote_toggleable)
    dialog.add_info("Create a local Git repository or connect it to a remote like GitHub").hide_row(hide=not remote_toggleable)

    dialog.add_text("<b>Repository URL</b>", var="repotext").hide_row(hide=hide_remote_settings)
    dialog.add_input(default=remote_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", enabled=remote_toggleable, width = 400, callback=update_dialog).hide_row(hide=hide_remote_settings)

    dialog.add_empty()
    dialog.add_button("Create", var="create", callback=create_repo, enabled=False).hide_row(hide=remote_enabled)
    dialog.add_button("Join", var="join", callback=clone_repo, enabled=False).hide_row(hide=hide_remote_settings)
    dialog.show()