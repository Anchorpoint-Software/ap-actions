import anchorpoint as ap
import time, os

script_dir = os.path.join(os.path.dirname(__file__), "..")

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    return len(ctx.project_id) == 0


def update_dialog(dialog: ap.Dialog, value):
    url = dialog.get_value("url")
    name = dialog.get_value("name")
    remote_enabled = dialog.get_value("remote")
    hide_remote_settings = not remote_enabled

    dialog.hide_row("repotext", hide_remote_settings)
    dialog.hide_row("url", hide_remote_settings)
    
    dialog.hide_row("join", hide_remote_settings)
    dialog.hide_row("create", remote_enabled)

    enable = len(name) > 0
    if not hide_remote_settings:
        enable = enable and len(url) > 0

    dialog.set_enabled("join", enable)
    dialog.set_enabled("create", enable)

def create_repo_async(repo_path, project_name):
    project = ctx.create_project(repo_path, project_name, ctx.workspace_id)

    repo = GitRepository.create(repo_path)
    helper.update_project(repo_path, None, False, None, project, False)
    repo.ignore(".ap/project.json", local_only=True)
    ap.UI().show_success("Git Repository Initialized")
    
    time.sleep(0.5)
    ap.UI().navigate_to_folder(repo_path)

def create_repo(dialog: ap.Dialog):
    name = dialog.get_value("name")
    repo_path = os.path.join(ctx.path, name)
    dialog.close()

    ctx.run_async(create_repo_async, repo_path, name)

def clone_repo_async(repo_path, url, project_name):
    os.mkdir(repo_path)
    with os.scandir(repo_path) as it:
        if any(it):
            ap.UI().show_info("Cannot Clone Git repository", "Folder must be empty")
            return
        
    try:
        progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
        repo = GitRepository.clone(url, repo_path, progress=helper.CloneProgress(progress))
        project = ctx.create_project(repo_path, project_name, ctx.workspace_id)
        helper.update_project(repo_path, url, False, None, project, False)
        repo.ignore(".ap/project.json", local_only=True)
        progress.finish()
        ap.UI().show_success("Git Repository Cloned")
        ap.UI().navigate_to_folder(repo_path)
    except Exception as e:
        ap.UI().show_error("Could not clone Git Repository", "You might have entered a wrong username / password, or you don't have access to the repository.")


def clone_repo(dialog: ap.Dialog):
    name = dialog.get_value("name")
    path = os.path.join(ctx.path, name)
    url = dialog.get_value("url")

    dialog.close()
    ctx.run_async(clone_repo_async, path, url, name)

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, script_dir)

    try:
        from vc.apgit.repository import * 
    except Warning as e:
        sys.exit(0)

    import git_repository_helper as helper
    sys.path.remove(script_dir)

    remote_enabled = True
    remote_url = ""

    hide_remote_settings = not remote_enabled
    ctx = ap.Context.instance()

    dialog = ap.Dialog()
    dialog.title = "Create Git Repository"
    dialog.icon = ctx.icon

    dialog.add_text("<b>Folder Name</b>")
    dialog.add_input(var="name", width = 400, callback=update_dialog, placeholder="Game_Engine_Files")
    dialog.add_info("Creating a Git repository will create a new project in Anchorpoint. <br> Learn more about <a href=\"https://docs.anchorpoint.app/docs/4-Collaboration/4-Workflow-Git/\">Git.</a>")
    dialog.add_switch(remote_enabled, var="remote", callback=update_dialog).add_text("Remote Repository")

    dialog.add_text("<b>Repository URL</b>", var="repotext").hide_row(hide=hide_remote_settings)
    dialog.add_input(default=remote_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", width = 400, callback=update_dialog).hide_row(hide=hide_remote_settings)

    dialog.add_empty()
    dialog.add_button("Create", var="create", callback=create_repo, enabled=False).hide_row(hide=remote_enabled)
    dialog.add_button("Join", var="join", callback=clone_repo, enabled=False).hide_row(hide=hide_remote_settings)
    dialog.show()