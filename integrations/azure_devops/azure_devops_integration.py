import anchorpoint as ap
import apsync as aps
from azure_devops_client import AzureDevOpsClient
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

        icon_path = os.path.join(ctx.yaml_dir, "azure_devops/logo.png")
        self.dashboard_icon = icon_path
        self.preferences_icon = icon_path
        self.is_setup = self.client.is_setup()

        if self.is_setup:
            success = self.client.setup_refresh_token()
            print(success)
            if success:
                self._setup_connected_actions()
            else:
                self._setup_reconnect_actions()
        else:
            self._setup_not_connected_actions()

    def _setup_not_connected_actions(self):
        self.preferences_actions.clear()
        connect = ap.IntegrationPreferenceAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = "azure_devops_connect"
        connect.tooltip = "Connect to Azure DevOps"
        self.preferences_actions.append(connect)

    def _setup_connected_actions(self):
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

    def _setup_reconnect_actions(self):
        self.preferences_actions.clear()
        reconnect = ap.IntegrationPreferenceAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = "azure_devops_reconnect"
        reconnect.tooltip = "Reconnect to Azure DevOps"
        self.preferences_actions.append(reconnect)
    
    def execute_preferences_action(self, actionId: str):
        if actionId == "azure_devops_connect":
            self.client.start_auth()
            self.start_auth()
        elif actionId == "azure_devops_disconnect":
            self.client.clear_integration()
            self._setup_not_connected_actions()
            self.is_setup = False
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
                ap.UI().show_error(title='Cannot load Azure DevOps Settings', duration=6000, description=f'Failed to load organization because "{str(e)}". Please try again.')
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
            self._setup_connected_actions()
            self.is_setup = True
            self.start_update()
        except Exception as e:
            ap.UI().show_error(title='Azure DevOps authentication failed', duration=6000, description=f'The authentication failed because "{str(e)}". Please try again.')
            return

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