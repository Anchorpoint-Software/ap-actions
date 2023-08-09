import anchorpoint as ap
import apsync as aps

from git_project import add_git_ignore

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
    if script_dir in sys.path: sys.path.remove(script_dir)

    ctx = ap.get_context()
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

    def clone_repo_async(repo_path: str, url: str, join_project_files, project, timeline_channel, workspace_id, patch_channel):
        with os.scandir(repo_path) as it:
            if any(it):
                ap.UI().show_info("Cannot Clone Git repository", "Folder must be empty")
                return
            
        try:
            progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
            repo = GitRepository.clone(url, repo_path, ctx.username, ctx.email, progress=helper.CloneProgress(progress))
            progress.finish()
            helper.update_project(repo_path, url, join_project_files, timeline_channel, project, True)
            add_git_ignore(repo, ctx, repo_path)
            if patch_channel:
                patch_timeline_channel(project, timeline_channel, workspace_id, url)

        except Exception as e:
            print(e)
            d = ap.Dialog()
            d.title = "Could not clone Git Repository"
            d.icon = ":/icons/versioncontrol.svg"

            remote_name = ""
            if "azure" in url or "visualstudio" in url:
                remote_name = "Azure DevOps"
            elif "github" in url:
                remote_name = "GitHub"
            elif "gitlab" in url:
                remote_name = "GitLab"
            elif "bitbucket" in url:
                remote_name = "Bitbucket"
            else:
                remote_name = "remote"

            d.add_info(f"You might have entered a wrong username / password, or you don't <br>have access to the <span style='color:white'>{remote_name} </span> repository. <a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/git/5-Git-troubleshooting'>Read more</a>")

            def retry():
                ctx.run_async(clone_repo_async, repo_path, url, join_project_files, project, timeline_channel, workspace_id, patch_channel)
                d.close()

            d.add_button("Retry", callback=lambda d: retry()).add_button("Close", callback=lambda d: d.close(), primary=False)
            d.show()
            raise e

    def patch_timeline_channel(project, timeline_channel, workspace_id, url):
        access = aps.get_workspace_access(workspace_id)
        if access == aps.AccessLevel.Owner or access == aps.AccessLevel.Admin:
            try:
                metadata = timeline_channel.metadata
                metadata["gitRemoteUrl"] = url
                timeline_channel.metadata = metadata
                aps.update_timeline_channel(project, timeline_channel)
            except:
                "Could not patch timeline channel"

    def is_location_same_repo(path: str, url: str):
        try:
            repo = GitRepository.load(path)
            if repo and url == repo.get_remote_url():
                return True
            return False
        except: 
            return False
        

    def join_repo(dialog: ap.Dialog, url, project, timeline_channel, ctx):
        location = dialog.get_value("location")
        if not url:
            url = dialog.get_value("url")
            patch_channel = True
        else:
            patch_channel = False

        dialog.close()
        
        if is_location_same_repo(location, url):
            repo = GitRepository.load(location)
            repo.set_username(ctx.username, ctx.email, location)
            helper.update_project(location, url, True, timeline_channel, project)
            add_git_ignore(repo, ctx, location)
        else:
            ctx.run_async(clone_repo_async, location, url, True, project, timeline_channel, ctx.workspace_id, patch_channel)

    def validate_path(dialog: ap.Dialog, value: str, url: str):
        if not value or len(value) == 0:
            return "Please add a folder for your project files"
        if not os.path.exists(value):
            return "Please add a real folder"
        if not helper.folder_empty(value):
            if not url:
                url = dialog.get_value("url")
            if is_location_same_repo(value, url):
                return
            return "Please pick an empty folder"
        return

    def validate_url(dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please add a Git repository URL"
        return

    def update_dialog(dialog: ap.Dialog, value):
        dialog.set_enabled("join", dialog.is_valid())

    dialog = ap.Dialog()
    dialog.title = "Join Git Repository"
    dialog.icon = ctx.icon
    
    path_placeholder = "Z:\\Projects\\ACME_Commercial"
    if platform.system() == "Darwin":
        path_placeholder = "/Projects/ACME_Commercial"    

    try:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
    except:
        remote_url = None

    dialog.add_text("<b>Project Folder</b>")
    dialog.add_info("Pick an empty folder to download the project files or tell Anchorpoint where your<br> repository is located")
    dialog.add_input(placeholder=path_placeholder, var="location", width=400, browse=ap.BrowseType.Folder, validate_callback=lambda d,v: validate_path(d,v,remote_url), callback=update_dialog)
    
    if not remote_url:
        dialog.add_text("<b>Repository URL</b>")
        dialog.add_input(placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", width=400, validate_callback=validate_url, callback=update_dialog)
        dialog.set_valid(False)

    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)
    
    dialog.add_button("Join", var="join", callback=lambda d: join_repo(d, remote_url, project, timeline_channel, ctx), enabled=False)
    dialog.show()