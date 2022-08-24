import sys, os
import time
import anchorpoint as ap
import apsync as aps

script_dir = os.path.join(os.path.dirname(__file__), "..")

def connect_repo_async(dialog, path, project):
    progress = ap.Progress("Opening Git Repository", show_loading_screen = True)
    dialog.close()

    sys.path.insert(0, script_dir)
    import git_repository_helper as helper
    try:
        from vc.apgit.repository import GitRepository 
    except Warning as e:
        return
    
    sys.path.remove(script_dir)

    repo = GitRepository.load(path)
    url = repo.get_remote_url()

    if project is None:
        project_name = dialog.get_value("name")
        project = ap.Context.instance().create_project(path, project_name)

    helper.update_project(path, url, False, None, project, add_path=False)
    repo.ignore(".ap/project.json", local_only=True)
    time.sleep(0.5)
    ap.UI().reload()

def on_folder_opened(ctx: ap.Context):
    sys.path.insert(0, script_dir)
    import git_repository_helper as helper
    sys.path.remove(script_dir)
    
    path = ctx.path
    
    def update_settings(dialog: ap.Dialog, value):
        settings = aps.Settings("connect_git_repo")
        settings.set(path, value)
        settings.store()

    def update_dialog(dialog: ap.Dialog, value):
        name = dialog.get_value("name")
        dialog.set_enabled("yes", len(name) > 0)
        
    def connect_repo(dialog: ap.Dialog, project):
        ctx.run_async(connect_repo_async, dialog, path, project)

    git_dir = os.path.join(ctx.path, ".git")
    if not os.path.exists(git_dir):
        return
    
    access = aps.get_workspace_access(ctx.workspace_id)
    if access not in [aps.AccessLevel.Owner, aps.AccessLevel.Admin]:
        return

    has_project = False
    project = None
    project_name = ""

    if len(ctx.project_id) > 0:
        project = aps.get_project(path)
        project_name = project.name

        channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
        if channel: 
            return

        # Only allow the git repository to be in the root of the project
        if project.path != path:
            return
    
    else:
        project_name = os.path.basename(path)

    settings = aps.Settings("connect_git_repo")
    never_ask_again = settings.get(path, False)
    if never_ask_again: 
        return

    dialog = ap.Dialog()
    dialog.title = "Open Git Repository"
    dialog.icon = ctx.icon

    dialog.add_text("<b>Project Name</b>")
    dialog.add_input(default=project_name, enabled=project is None, var="name", callback=update_dialog, width = 360)  
    dialog.add_info("Opening a Git repository as a project in Anchorpoint enables <br> certain actions in the project timeline. Learn more about <a href=\"https://docs.anchorpoint.app/docs/4-Collaboration/4-Workflow-Git/\">Git.</a>")
    dialog.add_checkbox(callback=update_settings, var="neveraskagain").add_text("Never ask again")
    dialog.add_button("Open Repository", enabled=has_project, var="yes", callback=lambda d: connect_repo(d,project)).add_button("Cancel", callback=lambda d: d.close())
    
    dialog.show()
    

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, script_dir)

    try:
        from vc.apgit.repository import * 
    except Warning as e:
        sys.exit(0)

    import platform
    import git_repository_helper as helper
    
    sys.path.remove(script_dir)

    ctx = ap.Context.instance()
    ui = ap.UI()

    project_id = ctx.project_id
    workspace_id = ctx.workspace_id
    project = aps.get_project_by_id(project_id, workspace_id)
    if not project:
        ui.show_error("Cannot connect git repository", "You must create a project first")
        sys.exit(0) 

    timeline_channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
    settings = aps.Settings()

    def connect_repo(dialog: ap.Dialog):
        location = dialog.get_value("location")
        repo_path = location
        if not GitRepository.is_repo(repo_path):
            ui.show_info("Could not connect Git Repository", "Folder does not contain a Git repo")
        else:
            repo = GitRepository.load(repo_path)
            if not repo:
                ui.show_error("Invalid Repo", "The git repository cannot be opened")
                return

            try:
                helper.update_project(repo_path, None, False, timeline_channel, project)
            except:
                ui.show_error("Could not connect Git Repository", "Folder does already contain an Anchorpoint project")
                return
            repo.ignore(".ap/project.json", local_only=True)
            ui.show_success("Git Repository Connected")
            dialog.close()

    def update_dialog(dialog: ap.Dialog, value):
        location = dialog.get_value("location")
        dialog.set_enabled("connect", len(location) > 0)

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
    dialog.title = "Connect Git repository"
    dialog.icon = ctx.icon

    dialog.add_text("<b>Git Project Folder</b>")
    if platform.system() == "Windows":
        dialog.add_input(placeholder="D:/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)
    else:
        dialog.add_input(placeholder="/users/johndoe/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)

    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)

    dialog.add_empty()
    dialog.add_button("Connect", var="connect", callback=connect_repo, enabled=False)
    dialog.show()