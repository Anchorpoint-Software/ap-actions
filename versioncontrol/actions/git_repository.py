from gc import callbacks
from time import time
import anchorpoint as ap
import apsync as aps
import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()

try:
    from vc.apgit.repository import * 
except Warning as e:
    sys.exit(0)

import platform

channel_id = "Git"

ctx = ap.Context.instance()
ui = ap.UI()

project_id = ctx.project_id
workspace_id = ctx.workspace_id
project = aps.get_project_by_id(project_id, workspace_id)
if not project:
    ui.show_error("Cannot create git repository", "You must create a project first")
    sys.exit(0) 

timeline_channel = aps.get_timeline_channel(project, channel_id)
is_join = ctx.type == ap.Type.JoinProjectFiles
settings = aps.Settings()

def update_project(repo_path: str, remote_url: Optional[str]):
    if not is_join:
        ap.add_path_to_project(repo_path, project_id, workspace_id)

        channel = aps.TimelineChannel()
        channel.id = channel_id
        channel.name = "Git Repository"
        channel.icon = aps.Icon(":/icons/versioncontrol.svg", "#D4AA37")

        folder_id = aps.get_folder_id(repo_path)

        metadata = {"gitPathId": folder_id}
        if remote_url:
            metadata["gitRemoteUrl"] = remote_url

        channel.metadata = metadata

        if not timeline_channel:
            aps.add_timeline_channel(project, channel)
            
        aps.set_folder_icon(repo_path, aps.Icon(":/icons/versioncontrol.svg", "#D4AA37"))
    else:
        ap.join_project_path(repo_path, project_id, workspace_id)
    pass
class CloneProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int):
        if operation_code == "downloading":
            self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")

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
        update_project(repo_path, None)
        repo.ignore(".ap/project.json", local_only=True)
        ui.show_success("Git Repository Initialized")
        dialog.close()

def retry_clone(dialog: ap.Dialog, repo_path: str, url: str):
    username = dialog.get_value("user")
    password = dialog.get_value("password")
    dialog.close()

    GitRepository.authenticate(url, username, password)
    ctx.run_async(clone_repo_async, repo_path, url)

def authenticate(repo_path: str, url: str):    
    from urllib.parse import urlparse

    dialog = ap.Dialog()
    dialog.title = "Authentication Failed"
    dialog.icon = ctx.icon
    
    host = urlparse(url).hostname
    dialog.add_text(f"We could not authenticate with <b>{host}</b>.<br>Please enter your credentials and try again.")
    dialog.add_text("<b>Username or Email</b>")
    dialog.add_input(var="user", width = 400)

    dialog.add_text("<b>Password</b>")
    dialog.add_input(var="password", width = 400, password=True)

    dialog.add_empty()
    dialog.add_button("Save and Retry", callback=lambda d: retry_clone(d, repo_path, url))
    dialog.show()

def clone_repo_async(repo_path: str, url: str):
    try:
        progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
        if not GitRepository.is_authenticated(url):
            if not url_gcm_supported(url):
                authenticate(repo_path, url)
            ui.show_error("Could not clone repository")
            return

        repo = GitRepository.clone(url, repo_path, progress=CloneProgress(progress))
        progress.finish()
        update_project(repo_path, url)
        repo.ignore(".ap/project.json", local_only=True)
        ui.show_success("Git Repository Cloned")
    except Exception as e:
        ui.show_error("Failed to clone Git Repository", str(e))

def clone_repo(dialog: ap.Dialog):
    location = dialog.get_value("location")
    url = dialog.get_value("url")
    repo_path = location
    if GitRepository.is_repo(repo_path):
        ui.show_info("Already a Git repo")
    else:
        dialog.close()
        ctx.run_async(clone_repo_async, repo_path, url)

def update_dialog(dialog: ap.Dialog, value):
    url = dialog.get_value("url")
    location = dialog.get_value("location")
    remote_enabled = dialog.get_value("remote")
    hide_remote_settings = not remote_enabled

    dialog.hide_row("repotext", hide_remote_settings)
    dialog.hide_row("url", hide_remote_settings)

    # Providers such as Gitea do not work with GCM, ask the user for credentials instead
    no_credentials_required = url_gcm_supported(url)
    dialog.hide_row("usertext",  no_credentials_required or hide_remote_settings)
    dialog.hide_row("user",  no_credentials_required or hide_remote_settings)
    dialog.hide_row("passwordtext", no_credentials_required or hide_remote_settings)
    dialog.hide_row("password", no_credentials_required or hide_remote_settings)
    
    dialog.hide_row("join", hide_remote_settings)
    dialog.hide_row("create", remote_enabled)

    dialog.set_enabled("join", len(location) > 0)
    dialog.set_enabled("create", len(location) > 0)

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