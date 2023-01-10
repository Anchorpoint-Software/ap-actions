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

def on_deeplink_opened(link: str, ctx: ap.Context):
    print(f"python: deeplink received: {link}")
    if "azure/auth" in link:
        d = ctx.get_dialog()
        if d and d.name == "git_repository":
            d.set_processing("provider_login", False)
            
        AzureClient.oauth2_response(link)


def on_timeout(ctx: ap.Context):
    pass
    # print("TIMEOUT")
    # d = ctx.get_dialog()
    # if d and d.name == "git_repository":
    #     print("ON TIMEOUT change value")
    #     d.set_processing("provider_login", False, None)

remote_repositories = []

if __name__ == "__main__":
    import sys, os, importlib
    script_dir = os.path.join(os.path.dirname(__file__), "..")
    sys.path.insert(0, script_dir)

    try:
        from vc.apgit.repository import * 
        from vc.apgit.azure import *
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
        ui.show_error("Cannot create git repository", "You must create a project first")
        sys.exit(0) 

    timeline_channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
    is_join = ctx.type == ap.Type.JoinProjectFiles
    settings = aps.Settings("git_repository")               

    def create_repo(dialog: ap.Dialog):
        repo_path = dialog.get_value("location")
 
        if GitRepository.is_repo(repo_path):
            ap.UI().show_info("Already a Git repo")
            return False

        repo = GitRepository.create(repo_path, ctx.username, ctx.email)
        helper.update_project(repo_path, None, is_join, timeline_channel, project)
        repo.ignore(".ap/project.json", local_only=True)
        repo.ignore("*.approj", local_only=True)
        ap.UI().show_success("Git Repository Initialized")
        dialog.close()
        return True
       
                

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
        provider = dialog.get_value("provider")

        if provider == "Manual":
            url = dialog.get_value("url")
        elif provider == "Azure DevOps":
            organization = dialog.get_value("organization_dropdown")
            repository = dialog.get_value("repository_dropdown")
            if repository == "Create New Repository":
                azure_client = AzureClient()
                if azure_client.init():
                    remote_repo = azure_client.create_project_and_repository(organization, project.name)
                    url = remote_repo.https_url
            else:
                global remote_repositories
                url = None
                for remote_repo in remote_repositories:
                    if remote_repo.display_name == repository:
                        url = remote_repo.https_url
                        break

        dialog.close()
        ctx.run_async(clone_repo_async, location, url, is_join)

    def update_dialog(dialog: ap.Dialog, value):
        url = dialog.get_value("url")
        location = dialog.get_value("location")
        remote_enabled = dialog.get_value("remote")
        provider = dialog.get_value("provider")
        hide_remote_settings = not remote_enabled

        dialog.hide_row("repotext", hide_remote_settings or provider != "Manual")
        dialog.hide_row("url", hide_remote_settings or provider != "Manual")
        
        dialog.hide_row("join", hide_remote_settings)
        dialog.hide_row("create", remote_enabled)

        enable = len(location) > 0
        if not hide_remote_settings and provider == "Manual":
            enable = enable and len(url) > 0

        dialog.set_enabled("join", enable)
        dialog.set_enabled("create", enable)

        settings.set("browse_path", location)
        settings.store()

    def login(dialog: ap.Dialog):
        dialog.set_processing("provider_login", True, "Connecting...")
        provider = dialog.get_value("provider")
        if provider == "Azure DevOps":
            client = AzureClient(True)
            client.init()
        
    def load_git_provider_account(dialog: ap.Dialog, provider: str):
        if not dialog:
            return

        if provider == "Azure DevOps":
            client = AzureClient()
            if client.init():
                user = client.get_user()
                dialog.set_value("provider_account_info", f"Logged in as: {user.display_name} (<i>{user.email}</i>)")

    def load_git_organizations(dialog: ap.Dialog, provider: str):
        if not dialog:
            return

        if provider == "Azure DevOps":
            client = AzureClient()
            if client.init():
                error = False
                try:
                    user = client.get_user()
                    organiztions = client.get_organizations(user)
                    error = len(organiztions) == 0
                except:
                    error = True
                    
                if error:
                    print("No Organizations Found")    
                else:
                    dialog.set_dropdown_values("organization_dropdown", organiztions[0], organiztions)

                dialog.set_processing("organization_dropdown", False)

    def load_git_repositories_async(dialog: ap.Dialog, organization: str, provider: str):
        if not dialog:
            return
        if provider == "Azure DevOps":
            client = AzureClient()
            if client.init():
                error_message = None
                is_admin = False
                try:
                    user = client.get_user()
                    repos = client.get_repositories(organization)
                    is_admin = client.user_is_admin(organization, user)
                    if is_admin:
                        dialog.set_value("organization_info", "You are an administator on Azure DevOps, you can create repositories and<br>invite members on Azure DevOps through the Anchorpoint integration")
                    else:
                        dialog.set_value("organization_info", "You have basic access on Azure DevOps. The Anchorpoint integration cannot create repositories and invite members on Azure DevOps<br>Ask the Azure DevOps administrator to add you to the <i>Project Collection Administrators</i> group")
                except AccessDeniedError as e:
                    error_message = "No Access"
                    dialog.set_value("organization_info", "You have no access to the Azure Organization<br>Talk to the administator of the Azure DevOps integration")
                except Exception as e:
                    error_message = "Error"

                if error_message:    
                    dialog.set_dropdown_values("repository_dropdown", error_message, [])
                    dialog.set_enabled("repository_dropdown", False)
                else:
                    global remote_repositories
                    remote_repositories = repos
                    
                    repositories = ["Create New Repository"] if is_admin else []
                    for repo in repos:
                        repositories.append(repo.display_name)

                    dialog.set_dropdown_values("repository_dropdown", repositories[0], repositories)
                    dialog.set_enabled("repository_dropdown", True)

                dialog.set_processing("repository_dropdown", False)

    def load_git_repositories(dialog: ap.Dialog, organization: str, provider: str):
        dialog.set_processing("repository_dropdown", True)
        ctx.run_async(load_git_repositories_async, dialog, organization, provider)

    def provider_changed(dialog: ap.Dialog, provider: str):
        if provider == "Manual":
            dialog.set_value("provider_info", "You can use an integration or type the repository URL manually")
            dialog.set_invisible_rows(["provider_login", "provider_account_info", "organization_dropdown", "organization_info", "repository_dropdown", "repository_info"])
            update_dialog(dialog, None)
        elif provider == "Azure DevOps":
            update_dialog(dialog, None)
            dialog.set_value("provider_info", "You can use an integration or type the repository URL manually<br>This integration allows Anchorpoint to create repositories and add users to projects on Azure DevOps")
            dialog.set_invisible_rows(["remote_repository", "remote_repository_info", "repotext", "url", "remote", "remote_info", "create"])

    remote_enabled = True
    remote_toggleable = not timeline_channel or "gitRemoteUrl" not in timeline_channel.metadata
    if not remote_toggleable:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
    else:
        remote_url = ""

    hide_remote_settings = not remote_enabled
    provider_logged_in = AzureClient.integration_active()

    dialog = ap.Dialog()
    dialog.name = "git_repository"
    dialog.title = "Git repository"
    dialog.icon = ctx.icon

    git_providers = ["Manual", "Azure DevOps"]
    active_git_provider = git_providers[1]
    dialog.add_text("Provider: ").add_dropdown(active_git_provider, git_providers, var="provider", callback=provider_changed)
    dialog.add_info("", var="provider_info")

    if not provider_logged_in:
        dialog.add_text("You are not logged in: ").add_button(f"Login to {active_git_provider}", var="provider_login",callback=login)
    else:
        dialog.add_text("Loading Account...", var="provider_account_info")
        dialog.add_separator()
        ctx.run_async(load_git_provider_account, dialog, active_git_provider)

        provider_organizations = [""]
        dialog.add_text("Organization: ").add_dropdown(provider_organizations[0], provider_organizations, enabled=provider_logged_in, var="organization_dropdown", callback=lambda d,v: load_git_repositories(d,v,dialog.get_value("provider")))
        dialog.add_info("Choose the Azure Organization to connect to.", var="organization_info")
        dialog.set_processing("organization_dropdown", True)
        ctx.run_async(load_git_organizations, dialog, active_git_provider)

        provider_repositories = []
        dialog.add_text("Repository: ").add_dropdown("", provider_repositories, enabled=provider_logged_in, var="repository_dropdown")
        dialog.add_info("Choose an existing repository or create a new one for this project", var="repository_info")
        dialog.set_processing("repository_dropdown", True)

        dialog.add_switch(remote_enabled, var="remote", callback=update_dialog).add_text("Remote Repository").hide_row()
        dialog.add_info("Create a local Git repository or connect it to a remote like GitHub", var="remote_info").hide_row()

        dialog.add_text("<b>Repository URL</b>", var="repotext").hide_row()
        dialog.add_input(default=remote_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", enabled=remote_toggleable, width = 400, callback=update_dialog).hide_row()
        
        dialog.add_separator()
        dialog.add_text("<b>Project Folder</b>")
        if platform.system() == "Windows":
            dialog.add_input(placeholder="D:/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)
        else:
            dialog.add_input(placeholder="/users/johndoe/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)

        browse_path = settings.get("browse_path")
        if browse_path is not None:
            dialog.set_browse_path(var="location", path=browse_path)

        dialog.add_empty()
        dialog.add_button("Create", var="create", callback=create_repo, enabled=False).hide_row(hide=remote_enabled)
        dialog.add_button("Join", var="join", callback=clone_repo, enabled=False).hide_row(hide=hide_remote_settings)

    provider_changed(dialog, active_git_provider)
    dialog.show()