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
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..")
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

    if ctx.type != ap.Type.JoinProjectFiles:
        sys.exit(0)

    project_id = ctx.project_id
    workspace_id = ctx.workspace_id
    project = aps.get_project_by_id(project_id, workspace_id)
    if not project:
        ui.show_error("Cannot create git repository", "You must create a project first")
        sys.exit(0) 

    timeline_channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
    settings = aps.Settings("git_repository")               

    def clone_repo_async(repo_path: str, url: str, join_project_files):
        with os.scandir(repo_path) as it:
            if any(it):
                ap.UI().show_info("Cannot Clone Git repository", "Folder must be empty")
                return
            
        try:
            progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
            repo = GitRepository.clone(url, repo_path, ctx.username, ctx.email, progress=helper.CloneProgress(progress))
            progress.finish()
            helper.update_project(repo_path, url, join_project_files, timeline_channel, project, True)
            repo.ignore(".ap/project.json", local_only=True)
            repo.ignore("*.approj", local_only=True)
        except Exception as e:
            d = ap.Dialog()
            d.title = "Could not clone Git Repository"
            d.icon = ":/icons/versioncontrol.svg"
            d.add_text("You might have entered a wrong username / password,<br>or you don't have access to the repository.")

            def retry():
                ctx.run_async(clone_repo_async, repo_path, url, join_project_files)
                d.close()

            d.add_button("Retry", callback=lambda d: retry()).add_button("Close", callback=lambda d: d.close())
            d.show()
            raise e

    def clone_repo(dialog: ap.Dialog):
        location = dialog.get_value("location")
        url = dialog.get_value("url")
        dialog.close()
        ctx.run_async(clone_repo_async, location, url, True)

    def validate_path(dialog: ap.Dialog, value: str):
        if not os.path.exists(value): 
            return "The folder for your project files must exist"
        if not helper.folder_empty(value):
            return "The folder for your project files must be empty"
        return

    def update_dialog(dialog: ap.Dialog, value):
        dialog.set_enabled("join", dialog.is_valid())

    try:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
    except:
        remote_url = ""

    dialog = ap.Dialog()
    dialog.title = "Join Git Repository"
    dialog.icon = ctx.icon

    path_placeholder = "Z:\\Projects\\ACME_Commercial"
    if platform.system() == "Darwin":
        path_placeholder = "/Projects/ACME_Commercial"    

    dialog.add_text("<b>Project Folder</b>")
    dialog.add_input(placeholder=path_placeholder, var="location", width = 400, browse=ap.BrowseType.Folder, validate_callback=validate_path, callback=update_dialog)
    
    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)

    dialog.add_text("<b>Repository URL</b>", var="repotext")
    dialog.add_input(default=remote_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", enabled=len(remote_url)==0, width = 400)

    dialog.add_empty()
    dialog.add_button("Join", var="join", callback=clone_repo, enabled=False)
    dialog.show()