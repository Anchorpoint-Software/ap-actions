import anchorpoint as ap
import apsync as aps
from azure_devops_client import *
import os

def on_load_integrations(integrations, ctx: ap.Context):
    integration = DevopsIntegration(ctx)
    integrations.add(integration)

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
        connect.identifier = "azure_devops_connect"
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
        disconnect.identifier = "azure_devops_disconnect"
        disconnect.tooltip = "Disconnect from Azure DevOps"
        self.preferences_actions.append(disconnect)

        settings = ap.IntegrationPreferenceAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = "azure_devops_settings"
        settings.tooltip = "Open settings for Azure DevOps integration"
        self.preferences_actions.append(settings)

        self.create_project_actions.clear()
        createRepo = ap.IntegrationCreateProjectAction()
        createRepo.name = "New Azure DevOps Repository"
        createRepo.identifier = "azure_devops_create_repo"
        createRepo.enabled = True
        createRepo.icon = aps.Icon(os.path.join(self.ctx.yaml_dir, "azure_devops/azureNew.svg"))
        self.create_project_actions.append(createRepo)

        existingRepo = ap.IntegrationCreateProjectAction()
        existingRepo.name = "Existing Azure DevOps Repository"
        existingRepo.identifier = "azure_devops_use_existing_repo"
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
        reconnect.identifier = "azure_devops_reconnect"
        reconnect.tooltip = "Reconnect to Azure DevOps"
        self.preferences_actions.append(reconnect)
        self.create_project_actions.clear()
        self.is_connected = False
    
    def execute_preferences_action(self, actionId: str):
        if actionId == "azure_devops_connect":
            self.client.start_auth()
            self.start_auth()
        elif actionId == "azure_devops_disconnect":
            self.client.clear_integration()
            self.is_setup = False
            self._setup_not_connected_state()
            self.start_update()
        elif actionId == "azure_devops_reconnect":
            self.client.start_auth()
        elif actionId == "azure_devops_settings":
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
        
    def setup_create_project_dialog_entries(self, actionId, dialog: ap.Dialog):
        if actionId == "azure_devops_create_repo":
            return []
        elif actionId == "azure_devops_use_existing_repo":
            dialog.add_dropdown("", [], var="azure_devops_repository_dropdown", callback=self.on_repository_selected)
            return ["azure_devops_repository_dropdown"]

    def on_create_project_dialog_entry_selected(self, actionId: str, dialog: ap.Dialog):
        if actionId == "azure_devops_use_existing_repo":
            self.ctx.run_async(load_git_repositories_async, self.client, dialog)

    def on_repository_selected(self, dialog: ap.Dialog, value):
        print(f"on_repository_selected called with value {value}")
        if value == "Pick a Repository":
            return
        dialog.set_valid(True)

    def org_callback(self, dialog: ap.Dialog, value):
        self.client.set_current_organization(value)

    def show_settings_dialog(self, current_org: str, organizations):
        dialog = ap.Dialog()
        dialog.name = "azure_devops_settings"
        dialog.title = "Azure DevOps"
        dialog.icon = ":/icons/wheel.svg"

        dialog.add_text("Organization", var="orgtext")
        dialog.add_dropdown(current_org, organizations, var="organization_dropdown", callback=self.org_callback)
        dialog.show()

def load_git_repositories_async(client, dialog: ap.Dialog):
    if not dialog:
        return
    
    current_value = dialog.get_value("azure_devops_repository_dropdown")
    print(f"current value: {current_value}")
    if current_value not in ["", "No Access", "Error"]:
        return

    dialog.set_valid(False)
    dialog.set_processing("azure_devops_repository_dropdown", True)
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
        dialog.set_dropdown_values("azure_devops_repository_dropdown", error_message, [])
        dialog.set_enabled("azure_devops_repository_dropdown", False)
    else:
        repositories = []
        for repo in repos:
            repositories.append(repo.display_name)

        dialog.set_dropdown_values("azure_devops_repository_dropdown", "Pick a Repository", repositories)
        dialog.set_enabled("azure_devops_repository_dropdown", True)

    dialog.set_processing("azure_devops_repository_dropdown", False)