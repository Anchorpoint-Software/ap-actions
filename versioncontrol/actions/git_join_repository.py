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

    def clone_repo_async(repo_path: str, url: str, join_project_files, project, timeline_channel, workspace_id, patch_channel, download_all, clearCredentials=False):
        with os.scandir(repo_path) as it:
            if any(it):
                ap.UI().show_info("Cannot Clone Git repository", "Folder must be empty")
                return
            
        try:
            progress = ap.Progress("Cloning Git Repository", show_loading_screen = True)
            if clearCredentials:
                host, path = GitRepository.get_git_url_info(url)
                GitRepository.erase_credentials(host, "https", path if "azure" or "visualstudio" in host else None)

            repo = GitRepository.clone(url, repo_path, ctx.username, ctx.email, progress=helper.CloneProgress(progress), sparse= not download_all)
            ap.evaluate_locks(workspace_id, project.id)
            progress.finish()
            helper.update_project(repo_path, url, join_project_files, timeline_channel, project, True)
            add_git_ignore(repo, ctx, repo_path)
            if patch_channel:
                patch_timeline_channel(project, timeline_channel, workspace_id, url)
            ap.reload_timeline_entries()
            ap.refresh_timeline_channel(timeline_channel.id)

        except Exception as e:
            ap.log_error(f"Cannot join Git Repository: {str(e)}")
            d = ap.Dialog()
            d.title = "Cannot join Git Repository"
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

            if remote_name == "Azure DevOps":
                d.add_info(f"You might have entered a wrong username / password, or you don't have access to the <span style='color:white'>{remote_name}</span> repository.<br>You can try the following:<br><br>1. Check to see if you can view the repository on <a href=\"{url}\">Azure DevOps</a>. If not, contact your project owner to get access.<br>2. Click \"Retry with relogin\" to input your username and password for Azure DevOps again.<br>3. Your project owner must grant you the <span color = \"white\">Basic Access Level</span> in the Organization Settings/Users in Azure DevOps.<br><br>If you are still having problems, please refer to our <a href='https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#i-don-t-have-access-to-the-azure-devops-repository'>documentation</a> or ask for help on our <a href='https://discord.gg/ZPyPzvx'>Discord server</a>.")
            elif remote_name == "GitHub":
                d.add_info(f"Anchorpoint cannot access the repository on <span style='color:white'>GitHub</span>. You can try the following: <br><br>1. If you have received an <span style='color:white'>email invitation</span> from GitHub, accept it first<br>2. Ensure that you have a valid GitHub account and access to the repository in your <a href=\"{url}\">web browser</a>.<br>3. If you have entered an <span style='color:white'>incorrect username</span> or password, navigate to “Project Settings” and click on “Git”. Then run “Clear Credentials”.<br><br>If you are still having problems, please refer to our <a href='https://docs.anchorpoint.app/docs/general/integrations/github/'>documentation</a> or ask for help on our <a href='https://discord.gg/ZPyPzvx'>Discord server</a>.")
            else:
                d.add_info(f"You might have entered a wrong username / password, or you don't<br>have access to the <span style='color:white'>{remote_name} </span> repository. <a href='https://docs.anchorpoint.app/docs/version-control/troubleshooting/'>Read more</a>")

            def retry(clearCredentials= False):
                ctx.run_async(clone_repo_async, repo_path, url, join_project_files, project, timeline_channel, workspace_id, patch_channel, download_all, clearCredentials)
                d.close()

            row = d.add_button("Retry", callback=lambda d: retry())
            if remote_name == "Azure DevOps":
                row = row.add_button("Retry with relogin", callback=lambda d: retry(clearCredentials=True), primary=False)
            row.add_button("Close", callback=lambda d: d.close(), primary=False)
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
            
            url_normalized = url
            repo_url_normalized = repo.get_remote_url()
            if url_normalized.endswith(".git"):
                url_normalized = url_normalized[:-4]
            if repo_url_normalized.endswith(".git"):
                repo_url_normalized = repo_url_normalized[:-4]

            if repo and url_normalized == repo_url_normalized:
                return True
            return False
        except: 
            return False
        

    def join_repo(dialog: ap.Dialog, url, project, timeline_channel, ctx):
        location = dialog.get_value("location")
        if ctx.has_team_features():
            download_all = dialog.get_value("download_all")
        else:
            download_all = True
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
            ap.reload_timeline_entries()
            ap.refresh_timeline_channel(timeline_channel.id)
        else:
            ctx.run_async(clone_repo_async, location, url, True, project, timeline_channel, ctx.workspace_id, patch_channel, download_all)

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
    
    def update_dialog_after_validate(dialog: ap.Dialog, isValid: bool):
        dialog.set_enabled("join", isValid)

    def update_dialog(dialog: ap.Dialog, value):
        info = get_dialog_info(value, "additional_info")
        dialog.set_value("additional_info", info)

    
    def get_dialog_info(url: str, info_type: str):
        services = {
            "dev.azure": ("Azure DevOps", ":/icons/organizations-and-products/AzureDevOps.svg", "Azure DevOps (Visual Studio)"),
            "visualstudio": ("Azure DevOps", ":/icons/organizations-and-products/AzureDevOps.svg", "Azure DevOps"),
            "github": ("GitHub", ":/icons/organizations-and-products/github.svg", "GitHub"),
            "gitlab": ("GitLab", ":/icons/organizations-and-products/gitlab.svg", "GitLab"),
            "bitbucket": ("Bitbucket", ":/icons/organizations-and-products/bitbucket.svg", "Bitbucket")
        }

        service_name, service_icon, service_info = ("Git", ":/icons/versioncontrol.svg", "your Git Server")

        for key in services.keys():
            if key in url:
                service_name, service_icon, service_info = services[key]
                break

        if info_type == "title":
            return f"Join {service_name} Repository"
        elif info_type == "icon":
            return service_icon
        elif info_type == "additional_info":
            return f"You may need to <b>log into</b> {service_info}."
        else:
            return None  # Handle invalid info_type if needed

    dialog = ap.Dialog()
    
    path_placeholder = "Z:\\Projects\\ACME_Commercial"
    if platform.system() == "Darwin":
        path_placeholder = "/Projects/ACME_Commercial"

    additional_info = None

    try:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
        dialog.title = get_dialog_info(remote_url, "title")
        dialog.icon = get_dialog_info(remote_url, "icon")
        additional_info = get_dialog_info(remote_url, "additional_info")
    except:
        dialog.title = "Join Git Repository"
        dialog.icon = ctx.icon
        remote_url = None

    dialog.add_text("<b>Project Folder</b>")
    dialog.add_info("Pick an empty folder to download the project files or tell Anchorpoint where your<br> repository is located")
    dialog.add_input(placeholder=path_placeholder, var="location", width=400, browse=ap.BrowseType.Folder, validate_callback=lambda d,v: validate_path(d,v,remote_url))
    
    if not remote_url:
        dialog.add_text("<b>Repository URL</b>")
        dialog.add_input(placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", width=400, validate_callback=validate_url, callback=update_dialog)

    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)

    if ctx.has_team_features():
        dialog.add_checkbox(True, text="Download Everything", var="download_all")

    if additional_info is not None:
        dialog.add_text(additional_info, var="additional_info")
    
    dialog.add_button("Join", var="join", callback=lambda d: join_repo(d, remote_url, project, timeline_channel, ctx), enabled=False)
    dialog.callback_validate_finsihed = update_dialog_after_validate
    dialog.show()