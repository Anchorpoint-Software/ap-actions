import anchorpoint as ap
import apsync as aps
from azure_devops_client import *
import os

connect_action_id = "azure_devops_connect"
disconnect_action_id = "azure_devops_disconnect"
reconnect_action_id = "azure_devops_reconnect"
settings_action_id = "azure_devops_settings"
create_repo_dialog_entry = "azure_devops_create_repo"
existing_repo_dialog_entry = "azure_devops_use_existing_repo"
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

class DevopsIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        self.client = AzureDevOpsClient(ctx.workspace_id)

        self.name = 'Azure DevOps'
        self.description = "Create repositories, add participants and do it all directly in Anchorpoint.<br>Each participant will need an Azure DevOps account. <a href'https://docs.anchorpoint.app/docs/2-manage-files/2-Cloud-NAS/'>Learn more</a> "
        self.priority = 100
        self.tags = ['git']
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
        createRepo.icon = aps.Icon(os.path.join(self.ctx.yaml_dir, "azure_devops/azureNew.svg"))
        self.create_project_actions.append(createRepo)

        existingRepo = ap.IntegrationCreateProjectAction()
        existingRepo.name = "Existing Azure DevOps Repository"
        existingRepo.identifier = existing_repo_dialog_entry
        existingRepo.enabled = True
        existingRepo.icon = aps.Icon(os.path.join(self.ctx.yaml_dir, "azure_devops/azure.svg"))
        self.create_project_actions.append(existingRepo)

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
        elif action_id == existing_repo_dialog_entry:
            dialog.add_dropdown("", [], var=repo_dropdown_entry, callback=self.on_repository_selected)
            return [repo_dropdown_entry]

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        if action_id == existing_repo_dialog_entry:
            self.ctx.run_async(load_git_repositories_async, self.client, dialog)

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_name: str):
        if action_id == create_repo_dialog_entry:
            self.create_new_repo(project_name)
        elif action_id == existing_repo_dialog_entry:
            self.use_existing_repo(dialog)

    def on_repository_selected(self, dialog: ap.Dialog, value):
        if value == "Pick a Repository":
            return
        dialog.set_valid(True)

    def org_callback(self, dialog: ap.Dialog, value):
        self.client.set_current_organization(value)

    def show_settings_dialog(self, current_org: str, organizations):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Azure DevOps"
        dialog.icon = ":/icons/wheel.svg"

        dialog.add_text("Organization", var="orgtext")
        dialog.add_dropdown(current_org, organizations, var="organization_dropdown", callback=self.org_callback)
        dialog.show()

    def create_new_repo(self, project_name: str) -> str:
        print(f"create new project {project_name}")
        current_org = self.client.get_current_organization()
        try:
            new_repo = self.client.create_project_and_repository(current_org, project_name)
            if new_repo is None:
                raise Exception("Failed to create project")
            return new_repo.https_url
        except Exception as e:
            ap.UI().show_error(title='Cannot create Azure DevOps Project', duration=6000, description=f'Failed to create, because "{str(e)}". Please try again.')
            raise e

    def use_existing_repo(self, dialog: ap.Dialog) -> str:
        value = dialog.get_value(repo_dropdown_entry)
        if value is None or value == "" or value == "Pick a Repository" or value == "No Access" or value == "Error":
            raise Exception("No repository selected")
        print(f"use existing project {value}")
        try:
            repo = self.client.get_project_by_name(value)
            if repo is None:
                raise Exception("Failed to find project")
            return repo.https_url
        except Exception as e:
            ap.UI().show_error(title='Cannot select Azure DevOps Project', duration=6000, description=f'Failed to select project {value}, because "{str(e)}". Please try again.')
            raise e

#needs to be outside of class otherwise crash in python execution
def load_git_repositories_async(client, dialog: ap.Dialog):
    if not dialog:
        return
    
    current_value = dialog.get_value(repo_dropdown_entry)
    if current_value not in ["", "No Access", "Error"]:
        return

    dialog.set_valid(False)
    dialog.set_processing(repo_dropdown_entry, True)
    organization = client.get_current_organization()
    error_message = None
    try:
        repos = client.get_repositories(organization)
    except AccessDeniedError as e:
        error_message = "No Access"
        ap.UI().show_error("Cannot load repositories", f"You have no access to the organization {organization}", 6000)
    except Exception as e:
        error_message = "Error"
        ap.UI().show_error("Cannot load repositories", f"Request failed with error {str(e)}", 6000)

    if error_message:    
        dialog.set_dropdown_values(repo_dropdown_entry, error_message, [])
        dialog.set_enabled(repo_dropdown_entry, False)
    else:
        repositories = []
        for repo in repos:
            repositories.append(repo.display_name)

        dialog.set_dropdown_values(repo_dropdown_entry, "Pick a Repository", repositories)
        dialog.set_enabled(repo_dropdown_entry, True)

    dialog.set_processing(repo_dropdown_entry, False)