import sys, os
import time
import anchorpoint as ap
import apsync as aps

script_dir = os.path.join(os.path.dirname(__file__), "..")

def connect_repo_async(ctx, dialog, path, project):
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
        repo.set_username(ctx.username, ctx.email, path)

    helper.update_project(path, url, False, None, project, add_path=False)
    repo.ignore(".ap/project.json", local_only=True)
    repo.ignore("*.approj", local_only=True)
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
        ctx.run_async(connect_repo_async, ctx, dialog, path, project)

    git_dir = os.path.join(ctx.path, ".git")
    if not os.path.exists(git_dir):
        return
    
    access = aps.get_workspace_access(ctx.workspace_id)
    if access not in [aps.AccessLevel.Owner, aps.AccessLevel.Admin]:
        return

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
    dialog.add_info("Opening a Git repository as a project in Anchorpoint enables <br> certain actions in the project timeline. Learn more about <a href=\"https://docs.anchorpoint.app/docs/4-Collaboration/5-Workflow-Git/\">Git.</a>")
    dialog.add_checkbox(callback=update_settings, var="neveraskagain").add_text("Never ask again")
    dialog.add_button("Open Repository", var="yes", callback=lambda d: connect_repo(d,project)).add_button("Cancel", callback=lambda d: d.close())
    
    dialog.show()