import anchorpoint as ap
import apsync as aps
from azure_devops_client import *
import os

integration_tags = ["git", "azure_devops"]
connect_action_id = "azure_devops_connect"
disconnect_action_id = "azure_devops_disconnect"
reconnect_action_id = "azure_devops_reconnect"
settings_action_id = "azure_devops_settings"
settings_org_dropdown_entry = "organization_dropdown"
create_repo_dialog_entry = "azure_devops_create_repo"
repo_dropdown_entry = "azure_devops_repository_dropdown"

def on_load_integrations(integrations, ctx: ap.Context):
    # for i in range(15):
    #     integration = DummyIntegration(ctx, i)
    #     integrations.add(integration)

    integration = DevopsIntegration(ctx)
    integrations.add(integration)

# class DummyIntegration(ap.ApIntegration):
#     def __init__(self, ctx: ap.Context, index: int):
#         super().__init__()
#         self.ctx = ctx
#         self.name = 'Dummy Integration'
#         self.description = "Some dummy integration for testing purposes"
#         self.priority = 101 + index
#         self.tags = ['git']

#         icon_path = os.path.join(ctx.yaml_dir, "azure_devops/logo.png")
#         self.dashboard_icon = icon_path
#         self.preferences_icon = icon_path
#         self.is_setup = False
#         self.is_connected = False

#     def execute_preferences_action(self, action_id: str):
#         print(f"execute_preferences_action {action_id}")

#     def on_auth_deeplink_received(self, url: str):
#         print(f"on_auth_deeplink_received {url}")

#     def supports_create_project(self, remote):
#         return False

#     def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
#         print(f"setup_create_project_dialog_entries {action_id}")

#     def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
#         print(f"on_create_project_dialog_entry_selected {action_id}")

#     def setup_project(self, action_id: str, dialog: ap.Dialog, project_name: str):
#         print(f"setup_project {action_id}")

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = AzureDevOpsClient(ctx.workspace_id)

    if not client.is_setup():
        return

    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=6000, description=f'Failed to get current organization. Please add manually.')
        return

    try:
        client.add_user_to_organization(current_org, email)
        ap.UI().show_success(title='User added to Azure DevOps', duration=3000, description=f'User {email} added to organization {current_org}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=10000, description=f'Failed to add user to organization, because "{str(e)}". Please add manually.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = AzureDevOpsClient(ctx.workspace_id)

    if not client.is_setup():
        return

    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot remove user to Azure DevOps', duration=6000, description=f'Failed to connect integration. Please remove manually.')
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot remove user to Azure DevOps', duration=6000, description=f'Failed to get current organization. Please remove manually.')
        return

    try:
        client.remove_user_from_organization(current_org, email)
        ap.UI().show_success(title='User removed from Azure DevOps', duration=3000, description=f'User {email} removed from organization {current_org}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove user from Azure DevOps', duration=10000, description=f'Failed to remove user from organization, because "{str(e)}". Please remove manually.')

def on_add_user_to_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot add user to Azure DevOps project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = AzureDevOpsClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add user to Azure DevOps project', duration=6000, description=f'Azure DevOps integration is not setup. Please add manually.')
        return
    
    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot add user to Azure DevOps project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        azureProject = client.get_project_by_name(current_org, project.name)
        client.add_user_to_project(current_org, email, azureProject.project_id)
        ap.UI().show_success(title='User added to Azure DevOps project', duration=3000, description=f'User {email} added to project {project.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot add user to Azure DevOps project', duration=10000, description=f'Failed to add user, because "{str(e)}". Please add manually.')
        return
    
def on_remove_user_from_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot remove user from Azure DevOps project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = AzureDevOpsClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove user from Azure DevOps project', duration=6000, description=f'Azure DevOps integration is not setup. Please add manually.')
        return
    
    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot remove user from Azure DevOps project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        client.remove_user_from_project(current_org, email, project.name)
        ap.UI().show_success(title='User removed from Azure DevOps project', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove user from Azure DevOps project', duration=10000, description=f'Failed to remove user, because "{str(e)}". Please add manually.')
        return

class DevopsIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        self.client = AzureDevOpsClient(ctx.workspace_id)

        self.name = 'Azure DevOps'
        self.description = "Create repositories, add participants and do it all directly in Anchorpoint.<br>Each participant will need an Azure DevOps account. <a href'https://docs.anchorpoint.app/docs/2-manage-files/2-Cloud-NAS/'>Learn more</a> "
        self.priority = 100
        self.tags = integration_tags
        self.repos_loaded = False

        icon_path = os.path.join(ctx.yaml_dir, "azure_devops/logo.png")
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

    def _setup_not_connected_state(self):
        self.preferences_actions.clear()
        connect = ap.IntegrationPreferenceAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to Azure DevOps"
        self.preferences_actions.append(connect)
        self.create_project_actions.clear()
        self.is_connected = False

    def _setup_connected_state(self):
        self.preferences_actions.clear()
        disconnect = ap.IntegrationPreferenceAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Disconnect from Azure DevOps"
        self.preferences_actions.append(disconnect)

        settings = ap.IntegrationPreferenceAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for Azure DevOps integration"
        self.preferences_actions.append(settings)

        self.create_project_actions.clear()
        createRepo = ap.IntegrationCreateProjectAction()
        createRepo.name = "New Azure DevOps Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/AzureDevOpsNew.svg")
        self.create_project_actions.append(createRepo)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.preferences_actions.clear()
        reconnect = ap.IntegrationPreferenceAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to Azure DevOps"
        self.preferences_actions.append(reconnect)
        self.create_project_actions.clear()
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
        elif action_id == settings_action_id:
            try:
                user = self.client.get_user()
                organizations = self.client.get_organizations(user)
                current_org = self.client.get_current_organization()
                if current_org is None:
                    current_org = organizations[0]
                    self.client.set_current_organization(current_org)
                self.show_settings_dialog(current_org, organizations)
            except Exception as e:
                ap.UI().show_error(title='Cannot load Azure DevOps Settings', duration=6000, description=f'Failed to load, because "{str(e)}". Please try again.')
                return

    def on_auth_deeplink_received(self, url: str):
        try:
            self.client.oauth2_response(response_url=url)
            user = self.client.get_user()
            organizations = self.client.get_organizations(user)
            if not organizations:
                raise Exception("No organizations found")

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
            ap.UI().show_error(title='Azure DevOps authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return

    def supports_create_project(self, remote):
        return any(azure_remote in remote for azure_remote in ["dev.azure.com", "visualstudio.com"])
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_name, progress)

    def on_repository_selected(self, dialog: ap.Dialog, value):
        if value == "Pick a Repository":
            return
        dialog.set_valid(True)

    def apply_org_callback(self, dialog: ap.Dialog):
        org = dialog.get_value(settings_org_dropdown_entry)
        self.client.set_current_organization(org)
        dialog.close()

    def show_settings_dialog(self, current_org: str, organizations):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Azure DevOps Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "azure_devops/azure.svg")

        dialog.add_text("<b>Organization</b>", var="orgtext")
        dialog.add_dropdown(current_org, organizations, var=settings_org_dropdown_entry)

        if len(organizations) > 1:
            dialog.add_info("It looks like you have multiple organizations on Azure DevOps.<br>Select the one you want to connect to this Anchorpoint workspace.")

        dialog.add_empty()
        dialog.add_button("Apply", var="apply", callback=self.apply_org_callback)
        dialog.show()

    def create_new_repo(self, project_name: str, progress: ap.Progress) -> str:
        current_org = self.client.get_current_organization()
        try:
            progress.set_text("Creating Azure DevOps Project")
            new_repo = self.client.create_project_and_repository(current_org, project_name)
            progress.set_text("")
            if new_repo is None:
                raise Exception("Failed to create project")
            return new_repo.https_url
        except Exception as e:
            if "project already exists" in str(e):
                ap.UI().show_error(title='Cannot create Azure DevOps Project', duration=8000, description=f'Failed to create, because project with name {project_name} already exists. Please try again.')
            else:
                ap.UI().show_error(title='Cannot create Azure DevOps Project', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again.')
            raise e