from gc import callbacks
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
    name = dialog.get_value("name")
    repo_path = os.path.join(path, name)
    if GitRepository.is_repo(repo_path):
        ui.show_info("Already a Git repo")
    else:
        repo = GitRepository.create(repo_path)
        ui.navigate_to_folder(repo_path)
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
        progress = ap.Progress("Cloning Git Repository")
        if not GitRepository.is_authenticated(url):
            if not url_gcm_supported(url):
                authenticate(repo_path, url)
            return

        repo = GitRepository.clone(url, repo_path, progress=CloneProgress(progress))
        progress.finish()
        ui.navigate_to_folder(repo_path)
        ui.show_success("Git Repository Cloned")
    except Exception as e:
        ui.show_error("Failed to clone Git Repository", str(e))

def clone_repo(dialog: ap.Dialog):
    name = dialog.get_value("name")
    url = dialog.get_value("url")
    repo_path = os.path.join(path, name)
    if GitRepository.is_repo(repo_path):
        ui.show_info("Already a Git repo")
    else:
        dialog.close()
        ctx.run_async(clone_repo_async, repo_path, url)

def update_dialog(dialog: ap.Dialog, value):
    url = dialog.get_value("url")
    name = dialog.get_value("name")
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

    dialog.set_enabled("join", len(name) > 0)
    dialog.set_enabled("create", len(name) > 0)



remote_enabled = True
hide_remote_settings = not remote_enabled

dialog = ap.Dialog()
dialog.title = "Git repository"
dialog.icon = ctx.icon
dialog.add_text("<b>Name</b>")
dialog.add_input(placeholder="My Repository Name", var="name", width = 400, callback=update_dialog)

dialog.add_switch(remote_enabled, var="remote", callback=update_dialog).add_text("Remote Repository")
dialog.add_info("Create a local Git repository or connect it to a remote like GitHub")

dialog.add_text("<b>Repository URL</b>", var="repotext").hide_row(hide=hide_remote_settings)
dialog.add_input(placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", width = 400, callback=update_dialog).hide_row(hide=hide_remote_settings)

dialog.add_empty()
dialog.add_button("Create", var="create", callback=create_repo, enabled=False).hide_row(hide=remote_enabled)
dialog.add_button("Join", var="join", callback=clone_repo, enabled=False).hide_row(hide=hide_remote_settings)
dialog.show()