import anchorpoint as ap
import apsync as aps
import webbrowser
from github_client import *
import os

integration_tags = ["git", "github"]
connect_action_id = "github_connect"
disconnect_action_id = "github_disconnect"
reconnect_action_id = "github_reconnect"
settings_action_id = "github_settings"
settings_org_dropdown_entry = "organization_dropdown"
create_repo_dialog_entry = "github_create_repo"
repo_dropdown_entry = "github_repository_dropdown"
integration_project_name_key = "project_name"

def on_load_integrations(integrations, ctx: ap.Context):
    integration = GithubIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)

    if not client.is_setup():
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot add member to GitHub', duration=6000, description='Failed to get current organization. Please add manually.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot add member to GitHub', duration=6000, description='Failed to connect integration. Please add manually.')
        return
    
    try:
        client.add_user_to_organization(current_org, email)
        ap.UI().show_success(title='Member added to GitHub', duration=3000, description=f'Member {email} added to organization {current_org.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot add member to GitHub', duration=10000, description=f'Failed to add member to organization, because "{str(e)}". Please add manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)

    if not client.is_setup():
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot remove member to GitHub', duration=6000, description='Failed to get current organization. Please remove manually.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot remove member to GitHub', duration=6000, description='Failed to connect integration. Please remove manually.')
        return
    
    try:
        client.remove_user_from_organization(current_org, email)
        ap.UI().show_success(title='Member removed from GitHub', duration=3000, description=f'Member {email} removed from organization {current_org.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove member from GitHub', duration=10000, description=f'Failed to remove member from organization, because "{str(e)}". Please remove manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')

def open_browser_and_close_dialog(dialog, url):
    print(f"{url} called for open in browser")
    webbrowser.open(url)
    dialog.close()

def on_add_user_to_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot add member to GitHub repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add member to GitHub repository', duration=6000, description='GitHub integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot add member to GitHub repository', duration=6000, description='Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.add_user_to_repository(current_org, email, project_name)
        ap.UI().show_success(title='Member added to GitHub repository', duration=3000, description=f'User {email} added to project {project.name}.')
    except Exception as e:
        repo_name = client.generate_github_project_name(project.name)
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            repo_name = integration_project_name
        
        import time
        time.sleep(1)
        dialog = ap.Dialog()
        dialog.title = "Cannot add member to GitHub repository"
        dialog.icon = ":/icons/organizations-and-products/github.svg"
        if "Organization is required." in str(e):
            dialog.add_info('No organization found. You have to add your member directly on GitHub.')
        elif "No matching member found." in str(e):
            dialog.add_info('It appears that the GitHub username is different from the member\'s email address. You have to add your member directly on GitHub.')
        else:
            dialog.add_info('It appears that the GitHub username is different from the member\'s email address. You have to add your member directly on GitHub.')
        dialog.add_button("Add Member on GitHub", callback=lambda d: open_browser_and_close_dialog(d, f'https://github.com/{current_org.login}/{repo_name}/settings/access'))
        dialog.show()
        return
    
def on_remove_user_from_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot remove member from GitHub repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove member from GitHub repository', duration=6000, description='GitHub integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot remove member from GitHub repository', duration=6000, description='Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.remove_user_from_repository(current_org, email, project_name)
        ap.UI().show_success(title='Member removed from GitHub repository', duration=3000, description=f'Member {email} removed from project {project.name}.')
    except Exception as e:
        repo_name = client.generate_github_project_name(project.name)
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            repo_name = integration_project_name
        if "Organization is required." in str(e):
            ap.UI().show_info(title='Cannot add member to GitHub repository', duration=8000, description=f'No organization found. You have to remove your member <a href="https://github.com/{current_org.login}/{repo_name}/settings/access">directly on GitHub</a>.')
        elif "No matching member found." in str(e):
            ap.UI().show_info(title='Cannot remove member from GitHub repository', duration=8000, description=f'No matching organisation member found. You have to remove your member <a href="https://github.com/{current_org.login}/{repo_name}/settings/access">directly on GitHub</a>.')
        else:
            ap.UI().show_error(title='Cannot remove member from GitHub repository', duration=10000, description=f'Failed to remove member, because "{str(e)}". You have to remove your member <a href="https://github.com/{current_org.login}/{repo_name}/settings/access">directly on GitHub</a>.')
        return
    
def retry_create_test_repo(client: GitHubClient, dialog):
    dialog.close()
    ctx = ap.get_context()
    ctx.run_async(create_test_repo_async, client)

def show_test_repo_error_dialog(client: GitHubClient, message):
    dialog = ap.Dialog()
    dialog.title = "We have found an issue"
    dialog.icon = ":/icons/organizations-and-products/github.svg"
    dialog.add_info(message)
    dialog.add_button("Retry", callback=lambda d: retry_create_test_repo(client, d), primary=True)
    dialog.show()

def create_test_repo_async(client: GitHubClient):
    current_org = client.get_current_organization()
    progress = None
    try:
        progress = ap.Progress("Testing GitHub Integration", "Creating Anchorpoint-Test repository", infinite=True, show_loading_screen=True)
        new_repo = client.create_repository(current_org, "Anchorpoint-Test")
        if new_repo is None:
            raise Exception("Created project not found")
    except Exception as e:
        def get_dialog_create_message(reason: str):
            return f"The Anchorpoint-Test repository could not be created, because {reason}.<br><br>Try the following:<br><br>1. Make sure, that you can open the <a href='https://github.com/{current_org.login}'>GitHub website</a> and have access to the selected organization.<br>2. Disconnect and connect the GitHub integration in Anchorpoint and retry the test.<br>3. Check our <a href='https://docs.anchorpoint.app/docs/general/integrations/github/#troubleshooting'>troubleshooting page</a> for more information.<br><br>If you have tried everything and the integration does not work, then create a<br>repository on the <a href='https://github.com/{current_org.login}'>GitHub website</a> and clone it via https."
        if "301" in str(e):
            show_test_repo_error_dialog(client, get_dialog_create_message("the organization was renamed or deleted"))
        elif "403" in str(e):
            show_test_repo_error_dialog(client, get_dialog_create_message(f"you do not have permission to create a repository in {current_org.name}"))
        elif "404" in str(e):
            show_test_repo_error_dialog(client, get_dialog_create_message("the organization could not be found"))
        else:
            ap.log_error(f"Github - Create Test Project Error: {str(e)}")
            show_test_repo_error_dialog(client, get_dialog_create_message("of an unknown error"))
        progress.finish()
        return
    
    import sys
    import os
    script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    temp_path = None
    try:
        progress.set_text("Cloning Anchorpoint-Test Repository")
        repo_url = new_repo.clone_url
        ctx = ap.get_context()
        import tempfile
        temp_path = tempfile.mkdtemp()
        GitRepository.clone(repo_url, temp_path, ctx.username, ctx.email)
    except Exception as e:
        def get_dialog_clone_message(reason: str):
            return f"The Anchorpoint-Test repository could not be cloned, because {reason}.<br><br>Try the following:<br><br>1. Make sure, that you can open the <a href='https://github.com/{current_org.login}'>GitHub website</a> and have access to the organization.<br>2. Disconnect and connect the GitHub integration in Anchorpoint and retry the test.<br>3. Check our <a href='https://docs.anchorpoint.app/docs/general/integrations/github/#troubleshooting'>troubleshooting page</a> for more information.<br><br>If you have tried everything and the integration does not work, then create a<br>repository on the <a href='https://github.com/{current_org.login}'>GitHub website</a> and clone it via https."
        message = str(e)
        print(f"Failed to clone test repo: {message}")
        ap.log_error(f"Github - Unknown Clone Test Repo Error: {message}")
        show_test_repo_error_dialog(client, get_dialog_clone_message("of an unknown error"))
        return
    finally:
        if temp_path is not None:
            import shutil
            try:
                shutil.rmtree(temp_path)
            except Exception as e:
                print(f"Failed to remove temp path: {str(e)}")
        if progress is not None:
            progress.finish()
        if script_dir in sys.path:
            sys.path.remove(script_dir)

    ap.UI().show_success(title='GitHub Integration Test sucessful', duration=3000, description='Test repository "Anchorpoint-Test" created and cloned successfully.')

class GithubIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        config = ap.get_config()
        self.client = GitHubClient(ctx.workspace_id, config.github_client_id, config.github_client_key)

        self.name = 'GitHub'
        self.description = "Create GitHub repositories directly in Anchorpoint. <a href='https://docs.anchorpoint.app/docs/general/integrations/github/'>Learn more</a>"
        self.priority = 99
        self.tags = integration_tags

        icon_path = os.path.join(ctx.yaml_dir, "github/logo.svg")
        self.dashboard_icon = icon_path
        self.preferences_icon = icon_path
        self.is_setup = self.client.is_setup()

        if self.is_setup:
            if self.client.setup_refresh_token():
                self._setup_connected_state()
            else:
                self._setup_reconnect_state()
        else:
            self._setup_not_connected_state()

        createRepo = ap.IntegrationAction()
        createRepo.name = "New GitHub Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/github.svg")
        self.add_create_project_action(createRepo)

    def _setup_not_connected_state(self):
        self.clear_preferences_actions()

        connect = ap.IntegrationAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to GitHub"
        self.add_preferences_action(connect)
        self.is_connected = False

    def _setup_connected_state(self):
        self.clear_preferences_actions()

        disconnect = ap.IntegrationAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Disconnect from GitHub"
        self.add_preferences_action(disconnect)

        settings = ap.IntegrationAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for GitHub integration"
        self.add_preferences_action(settings)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.clear_preferences_actions()

        reconnect = ap.IntegrationAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to GitHub"
        self.add_preferences_action(reconnect)
        self.is_connected = False
    
    def execute_preferences_action(self, action_id: str):
        if action_id == connect_action_id:
            self.client.start_auth()
            self.start_auth()
        elif action_id == disconnect_action_id:
            self.client.clear_integration()
            self.is_setup = False
            self._setup_not_connected_state()
            self.start_update()
        elif action_id == reconnect_action_id:
            self.client.start_auth()
            self.start_auth()
        elif action_id == settings_action_id:
            try:
                organizations = self.client.get_organizations()
                if not organizations:
                    raise Exception("Failed to load organizations")
                current_org = self.client.get_current_organization()
                if current_org is None:
                    current_org = organizations[0]
                    self.client.set_current_organization(current_org)
                self.show_settings_dialog(current_org, organizations)
            except Exception as e:
                ap.UI().show_error(title='Cannot load GitHub Settings', duration=6000, description=f'Failed to load, because "{str(e)}". Please try again.')
                return

    def on_auth_deeplink_received(self, url: str):
        try:
            self.client.oauth2_response(response_url=url)
            organizations = self.client.get_organizations()
            if not organizations:
                raise Exception("Failed to load organizations")
            current_org = self.client.get_current_organization()
            if current_org is None:
                current_org = organizations[0]
                self.client.set_current_organization(current_org)
            if len(organizations) > 1:
                self.show_settings_dialog(current_org, organizations)
            self._setup_connected_state()
            self.is_setup = True
            self.is_connected = True
            self.start_update()
        except Exception as e:
            if "Connection aborted" in str(e):
                ap.UI().show_error(title='GitHub authentication failed', duration=6000, description='The authentication failed, because the connection was aborted. Please try again.')
            else:
                ap.log_error(f"Github - Unknown Auth Error: {str(e)}")
                ap.UI().show_error(title='GitHub authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_id:str, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_id, project_name, progress)

    def create_test_repo_btn_callback(self, dialog: ap.Dialog):
        dialog.close()
        ctx = ap.get_context()
        ctx.run_async(create_test_repo_async, self.client)

    def apply_org_callback(self, dialog: ap.Dialog, value, organizations):
        org = next((x for x in organizations if x.name == value), None)
        if org is None:
            return
        print("Selected organization: " + org.name)
        self.client.set_current_organization(org)

    def show_settings_dialog(self, current_org, organizations):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "GitHub Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "github/logo.svg")

        dialog.add_text("<b>1. Account</b>", var="accounttext")
        dialog.add_text(organizations[0].name)
        dialog.add_empty()

        dialog.add_text("<b>2. Organization</b>", var="orgtext")

        dropdown_entries = []

        for org in organizations:
            entry = ap.DropdownEntry()
            entry.name = org.name
            if org.avatar_url is not None:
                entry.icon = org.avatar_url
            else:
                entry.icon = ":/icons/organizations-and-products/github.svg"
            entry.use_icon_color = True
            dropdown_entries.append(entry)

        dialog.add_dropdown(current_org.name, dropdown_entries, callback=lambda d, v: self.apply_org_callback(d,v, organizations), var=settings_org_dropdown_entry)

        if len(organizations) > 1:
            dialog.add_info("It looks like you are member of organizations on GitHub.<br>Select the one you want to connect to this Anchorpoint<br>workspace or use your personal account.")

        dialog.add_empty()

        dialog.add_text("<b>3. Test Integration</b>")
        dialog.add_info("Anchorpoint will create and clone a repository called<br>\"Anchorpoint-Test\" to check if the integration is working<br>properly. You can delete this repository later.")
        dialog.add_button("Create Test Repository", callback=lambda d: self.create_test_repo_btn_callback(d))
        dialog.add_empty()

        dialog.show()

    def create_new_repo(self, project_id:str, project_name: str, progress: ap.Progress) -> str:
        current_org = self.client.get_current_organization()
        try:
            progress.set_text("Creating GitHub Repository")
            new_repo = self.client.create_repository(current_org, project_name)
            settings = aps.SharedSettings(project_id, self.ctx.workspace_id, "integration_info")
            settings.set(integration_project_name_key, new_repo.name)
            settings.store()
            progress.set_text("")
            if new_repo is None:
                raise Exception("Created repository not found")
            return new_repo.clone_url
        except Exception as e:
            if "already exists" in str(e):
                ap.UI().show_error(title='Cannot create GitHub Repository', duration=8000, description=f'Failed to create, because repository with name {project_name} already exists. Please try again.')
            else:
                ap.log_error(f"Github - Unknown Create Project Error: {str(e)}")
                ap.UI().show_error(title='Cannot create GitHub Repository', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/general/integrations/github">troubleshooting</a>.')
            raise e