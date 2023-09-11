import anchorpoint as ap
import apsync as aps
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

def on_load_integrations(integrations, ctx: ap.Context):
    integration = GithubIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)

    if not client.is_setup():
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot add user to GitHub', duration=6000, description=f'Failed to get current organization. Please add manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot add user to GitHub', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    try:
        client.add_user_to_organization(current_org, email)
        ap.UI().show_success(title='User added to GitHub', duration=3000, description=f'User {email} added to organization {current_org.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot add user to GitHub', duration=10000, description=f'Failed to add user to organization, because "{str(e)}". Please add manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)

    if not client.is_setup():
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot remove user to GitHub', duration=6000, description=f'Failed to get current organization. Please remove manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot remove user to GitHub', duration=6000, description=f'Failed to connect integration. Please remove manually.')
        return
    
    try:
        client.remove_user_from_organization(current_org, email)
        ap.UI().show_success(title='User removed from GitHub', duration=3000, description=f'User {email} removed from organization {current_org.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove user from GitHub', duration=10000, description=f'Failed to remove user from organization, because "{str(e)}". Please remove manually <a href="https://github.com/orgs/{current_org.login}/people">here</a>.')

def on_add_user_to_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot add user to GitHub repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add user to GitHub repository', duration=6000, description=f'GitHub integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot add user to GitHub repository', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        client.add_user_to_repository(current_org, email, project.name)
        ap.UI().show_success(title='User added to GitHub repository', duration=3000, description=f'User {email} added to project {project.name}.')
    except Exception as e:
        if "Organization is required." in str(e):
            ap.UI().show_info(title='Cannot add user to GitHub repository', duration=8000, description=f'No organization found. Please add manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        elif "No matching member found." in str(e):
            ap.UI().show_info(title='Cannot add user to GitHub repository', duration=8000, description=f'No matching organisation member found. Please add manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        else:
            ap.UI().show_error(title='Cannot add user to GitHub repository', duration=10000, description=f'Failed to add user, because "{str(e)}". Please add manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        return
    
def on_remove_user_from_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot remove user from GitHub repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitHubClient(ctx.workspace_id, ap.get_config().github_client_id, ap.get_config().github_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove user from GitHub repository', duration=6000, description=f'GitHub integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot remove user from GitHub repository', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        client.remove_user_from_repository(current_org, email, project.name)
        ap.UI().show_success(title='User removed from GitHub repository', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        if "Organization is required." in str(e):
            ap.UI().show_info(title='Cannot add user to GitHub repository', duration=8000, description=f'No organization found. Please remove manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        elif "No matching member found." in str(e):
            ap.UI().show_info(title='Cannot remove user from GitHub repository', duration=8000, description=f'No matching organisation member found. Please remove manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        else:
            ap.UI().show_error(title='Cannot remove user from GitHub repository', duration=10000, description=f'Failed to remove user, because "{str(e)}". Please remove manually <a href="https://github.com/{current_org.login}/{project.name}/settings/access">here</a>.')
        return

class GithubIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        config = ap.get_config()
        self.client = GitHubClient(ctx.workspace_id, config.github_client_id, config.github_client_key)

        self.name = 'GitHub'
        self.description = "Create repositories, add participants and do it all directly in Anchorpoint.<br>Each participant will need an GitHub account. <a href='https://docs.anchorpoint.app/docs/1-overview/integrations/github/'>Learn more</a>"
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
            ap.UI().show_error(title='GitHub authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_name, progress)

    def apply_org_callback(self, dialog: ap.Dialog, organizations):
        org_name = dialog.get_value(settings_org_dropdown_entry)
        org = next((x for x in organizations if x.name == org_name), None)
        if org is None:
            return
        self.client.set_current_organization(org)
        dialog.close()

    def show_settings_dialog(self, current_org, organizations):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "GitHub Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "github/logo.svg")

        dialog.add_text("<b>Account</b>", var="accounttext")
        dialog.add_text(organizations[0].name)

        dialog.add_text("<b>Organization</b>", var="orgtext")

        dropdown_entries = []

        for org in organizations:
            entry = ap.DropdownEntry()
            entry.name = org.name
            entry.icon = org.avatar_url
            entry.use_icon_color = True
            dropdown_entries.append(entry)

        dialog.add_dropdown(current_org.name, dropdown_entries, var=settings_org_dropdown_entry)

        if len(organizations) > 1:
            dialog.add_info("It looks like you are member of organizations on GitHub.<br>Select the one you want to connect to this Anchorpoint workspace<br>or use your personal account.")

        dialog.add_empty()
        dialog.add_button("Apply", var="apply", callback=lambda d: self.apply_org_callback(d, organizations))
        dialog.show()

    def create_new_repo(self, project_name: str, progress: ap.Progress) -> str:
        current_org = self.client.get_current_organization()
        try:
            progress.set_text("Creating GitHub Repository")
            new_repo = self.client.create_repository(current_org, project_name)
            progress.set_text("")
            if new_repo is None:
                raise Exception("Created repository not found")
            return new_repo.clone_url
        except Exception as e:
            if "already exists" in str(e):
                ap.UI().show_error(title='Cannot create GitHub Repository', duration=8000, description=f'Failed to create, because repository with name {project_name} already exists. Please try again.')
            else:
                ap.UI().show_error(title='Cannot create GitHub Repository', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/1-overview/integrations/github">troubleshooting</a>.')
            raise e