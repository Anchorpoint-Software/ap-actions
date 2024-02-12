import anchorpoint as ap
import apsync as aps
import webbrowser
import urllib.parse 
from azure_devops_client import *
import os

integration_tags = ["git", "azure_devops"]
devops_root = "dev.azure.com"
connect_action_id = "azure_devops_connect"
disconnect_action_id = "azure_devops_disconnect"
reconnect_action_id = "azure_devops_reconnect"
settings_action_id = "azure_devops_settings"
settings_org_dropdown_entry = "organization_dropdown"
settings_credential_btn_entry = "credential_btn"
settings_credential_btn_highlight_entry = "credential_btn_highlight"
settings_policies_btn_entry = "policies_btn"
settings_policies_btn_highlight_entry = "policies_btn_highlight"
create_repo_dialog_entry = "azure_devops_create_repo"
repo_dropdown_entry = "azure_devops_repository_dropdown"
create_dialog_info_entry = "azure_devops_create_dialog_info"
integration_project_name_key = "project_name"

def on_load_integrations(integrations, ctx: ap.Context):
    integration = DevopsIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = AzureDevOpsClient(ctx.workspace_id)

    if not client.is_setup():
        return

    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=6000, description=f'Failed to get current organization. Please add manually <a href="https://{devops_root}/{current_org}/_settings/users">here</a>.')
        return

    try:
        client.add_user_to_organization(current_org, email)
        ap.UI().show_success(title='User added to Azure DevOps', duration=3000, description=f'User {email} added to organization {current_org}.')
    except BillingSetupRequiredException as bsre:
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=10000, description=f'You need to setup <a href="{bsre.href_url}">billing</a> to invite more members.')
    except Exception as e:
        ap.UI().show_error(title='Cannot add user to Azure DevOps', duration=10000, description=f'Failed to add user to organization, because "{str(e)}". Please add manually <a href="https://{devops_root}/{current_org}/_settings/users">here</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = AzureDevOpsClient(ctx.workspace_id)

    if not client.is_setup():
        return

    if not client.setup_refresh_token():
        ap.UI().show_error(title='Cannot remove user to Azure DevOps', duration=6000, description=f'Failed to connect integration. Please remove manually.')
        return
    
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot remove user to Azure DevOps', duration=6000, description=f'Failed to get current organization. Please remove manually <a href="https://{devops_root}/{current_org}/_settings/users">here</a>.')
        return

    try:
        client.remove_user_from_organization(current_org, email)
        ap.UI().show_success(title='User removed from Azure DevOps', duration=3000, description=f'User {email} removed from organization {current_org}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove user from Azure DevOps', duration=10000, description=f'Failed to remove user from organization, because "{str(e)}". Please remove manually <a href="https://{devops_root}/{current_org}/_settings/users">here</a>.')

def open_browser_and_close_dialog(dialog, url):
    webbrowser.open(url)
    dialog.close()

def show_add_member_error_dialog(title, message, url, btn_text):
    import time
    time.sleep(1)
    dialog = ap.Dialog()
    dialog.title = title
    dialog.icon = ":/icons/organizations-and-products/AzureDevOps.svg"
    dialog.add_info(message)
    dialog.add_button(btn_text, callback=lambda d: open_browser_and_close_dialog(d, url))
    dialog.show()

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
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        azureProject = client.get_project_by_name(current_org, project_name)
        client.add_user_to_project(current_org, email, azureProject.project_id)
        ap.UI().show_success(title='User added to Azure DevOps project', duration=3000, description=f'User {email} added to project {project.name}.')
    except BillingSetupRequiredException as bsre:
        show_add_member_error_dialog("Cannot add user to Azure DevOps", f"You need to setup billing to invite more members.", bsre.href_url, "Setup Billing")
    except Exception as e:
        encoded_project_name = urllib.parse.quote(project_name)
        project_url = f'https://dev.azure.com/{current_org}/{encoded_project_name}/_settings/teams'
        show_add_member_error_dialog("Cannot add user to Azure DevOps project", f'Failed to add user, because "{str(e)}".<br>Please add user manually.', project_url, "Add User on Azure DevOps")
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
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.remove_user_from_project(current_org, email, project_name)
        ap.UI().show_success(title='User removed from Azure DevOps project', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        ap.UI().show_error(title='Cannot remove user from Azure DevOps project', duration=10000, description=f'Failed to remove user, because "{str(e)}". Please add manually.')
        return

def setup_credentials_async(dialog, org: str):
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    try:
        dialog.set_processing(settings_credential_btn_highlight_entry, True, "Updating")
        dialog.set_processing(settings_credential_btn_entry, True, "Updating")
        GitRepository.erase_credentials(devops_root, "https", org)
        result = GitRepository.get_credentials(devops_root, "https", org)
        if (result is None or result.get("host") is None or result["host"] != devops_root 
            or result.get("path") is None or result["path"] != org 
            or result.get("username") is None or result.get("password") is None):
            raise Exception("Login failed")
        GitRepository.store_credentials(devops_root, "https", result["username"], result["password"], org)
        ap.UI().show_success(title='Azure DevOps credentials stored', duration=3000, description=f'Azure DevOps credentials stored successfully.')
    except Exception as e:
        print(f"Failed to store Azure DevOps credentials: {str(e)}")
        ap.UI().show_error(title='Cannot store Azure DevOps credentials', duration=10000, description=f'Please visit our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#could-not-store-credentials">troubleshooting</a> page to learn how to fix this.')
    finally:
        dialog.set_processing(settings_credential_btn_highlight_entry, False)
        dialog.set_processing(settings_credential_btn_entry, False)
        if script_dir in sys.path:
            sys.path.remove(script_dir)

class DevopsIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        self.client = AzureDevOpsClient(ctx.workspace_id)

        self.name = 'Azure DevOps'
        self.description = "Create repositories, add members and do it all directly in Anchorpoint.<br>Each member will need an Azure DevOps account. <a href='https://docs.anchorpoint.app/docs/general/integrations/azure-devops/'>Learn more</a>"
        self.priority = 100
        self.tags = integration_tags

        icon_path = os.path.join(ctx.yaml_dir, "azure_devops/logo.svg")
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
        createRepo.name = "New Azure DevOps Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/AzureDevOps.svg")
        self.add_create_project_action(createRepo)

    def _setup_not_connected_state(self):
        self.clear_preferences_actions()

        connect = ap.IntegrationAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to Azure DevOps"
        self.add_preferences_action(connect)
        self.is_connected = False

    def _setup_connected_state(self):
        self.clear_preferences_actions()

        disconnect = ap.IntegrationAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Disconnect from Azure DevOps"
        self.add_preferences_action(disconnect)

        settings = ap.IntegrationAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for Azure DevOps integration"
        self.add_preferences_action(settings)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.clear_preferences_actions()

        reconnect = ap.IntegrationAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to Azure DevOps"
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
                user = self.client.get_user()
                organizations = self.client.get_organizations(user)
                current_org = self.client.get_current_organization()
                display_name = self.client.get_user().display_name
                if current_org is None:
                    if not organizations:
                        raise Exception("Organizations list is empty")
                    current_org = organizations[0]
                    self.client.set_current_organization(current_org)
                self.show_settings_dialog(current_org, display_name, organizations)
            except Exception as e:
                if "Organizations list is empty" in str(e):
                    ap.UI().show_error(title='Cannot load Azure DevOps Settings', duration=6000, description=f'Failed to load, because no organizations where found. Please try again or visit our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/">troubleshooting</a> page.')
                else:
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
            display_name = self.client.get_user().display_name
            if current_org is None:
                current_org = organizations[0]
                self.client.set_current_organization(current_org)
            self.show_settings_dialog(current_org, display_name, organizations)
            self._setup_connected_state()
            self.is_setup = True
            self.is_connected = True
            self.start_update()
        except Exception as e:
            if "No organizations found" in str(e):
                ap.UI().show_error(title='Azure DevOps authentication failed', duration=6000, description=f'No organizations found. Please visit our <a href="https://docs.anchorpoint.app/docs/1-overview/integrations/azure-devops/#troubleshooting">troubleshooting</a> page to learn how to fix this.')
            elif "Connection aborted" in str(e):
                ap.UI().show_error(title='Azure DevOps authentication failed', duration=6000, description=f'The authentication failed, because the connection was aborted. Please try again or visit our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#troubleshooting">troubleshooting</a> page.')
            else:
                ap.UI().show_error(title='Azure DevOps authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please visit our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#troubleshooting">troubleshooting</a> page to learn how to fix this.')
            return
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            if self.is_setup:
                dialog.add_info("You may need to <b>log into</b> Azure DevOps (Visual Studio) again after the final step.", var=create_dialog_info_entry)
                return [create_dialog_info_entry]
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_id: str, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_id, project_name, progress)

    def change_org_callback(self, dialog: ap.Dialog, value: str):
        self.client.set_current_organization(value)
        dialog.hide_row(settings_credential_btn_entry, True)
        dialog.hide_row(settings_credential_btn_highlight_entry, False)
        dialog.hide_row(settings_policies_btn_entry, True)
        dialog.hide_row(settings_policies_btn_highlight_entry, False)

    def credential_btn_callback(self, dialog: ap.Dialog):
        dialog.hide_row(settings_credential_btn_entry, False)
        dialog.hide_row(settings_credential_btn_highlight_entry, True)
        ctx = ap.get_context()
        org = self.client.get_current_organization()
        ctx.run_async(setup_credentials_async, dialog, org)
         
    def policies_btn_callback(self, dialog: ap.Dialog):
        import webbrowser
        org = self.client.get_current_organization()
        webbrowser.open(f"https://{devops_root}/{org}/_settings/organizationPolicy")
        dialog.hide_row(settings_policies_btn_entry, False)
        dialog.hide_row(settings_policies_btn_highlight_entry, True)
        

    def show_settings_dialog(self, current_org: str, display_name: str, organizations):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Azure DevOps Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "azure_devops/logo.svg")

        dialog.add_text("<b>1. Organization</b>", var="orgtext")
        dialog.add_dropdown(current_org, organizations, var=settings_org_dropdown_entry, callback=self.change_org_callback)
        dialog.add_info("Allow Anchorpoint to create repositories and add<br>members in a dedicated organization.")
        dialog.add_empty()

        dialog.add_text("<b>2. Git Credentials</b>")
        dialog.add_image(os.path.join(self.ctx.yaml_dir, "azure_devops/credentialManager.webp"),width=230)
        dialog.add_info("Opens the Git Credential Manager, where you need to<br>enter your Azure DevOps login data to grant Anchorpoint<br>permission to upload and download files.")
        dialog.add_button("Enter your Azure DevOps Credentials", var=settings_credential_btn_highlight_entry, callback=self.credential_btn_callback)
        dialog.add_button("Enter your Azure DevOps Credentials", var=settings_credential_btn_entry, callback=self.credential_btn_callback, primary=False)
        dialog.hide_row(settings_credential_btn_entry, True)
        dialog.add_empty()

        dialog.add_text("<b>3. Permissions</b>")
        dialog.add_image(os.path.join(self.ctx.yaml_dir, "azure_devops/devopsImage.webp"),width=330)
        dialog.add_info("In Organization Settings/Policies, enable “Third-party<br>application access via OAuth” to make the integration work.")
        dialog.add_button("Check OAuth Policies", var=settings_policies_btn_highlight_entry, callback=self.policies_btn_callback)
        dialog.add_button("Check OAuth Policies", var=settings_policies_btn_entry, callback=self.policies_btn_callback, primary=False)
        dialog.hide_row(settings_policies_btn_entry, True)

        dialog.show()

    def create_new_repo(self, project_id:str, project_name: str, progress: ap.Progress) -> str:
        current_org = self.client.get_current_organization()
        try:
            progress.set_text("Creating Azure DevOps Project")
            new_repo = self.client.create_project_and_repository(current_org, project_name)
            settings = aps.SharedSettings(project_id, self.ctx.workspace_id, "integration_info")
            print(f"git repo name saved in integration_info: {new_repo.display_name}")
            settings.set(integration_project_name_key, new_repo.display_name)
            settings.store()

            progress.set_text("")
            if new_repo is None:
                raise Exception("Created project not found")
            return new_repo.https_url
        except Exception as e:
            if "TF50309" in str(e):
                ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                   duration=8000, 
                                   description=f'Failed to create, because you do not have permission to create projects in the {current_org} organization. Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#member-cannot-create-azure-devops-projects-from-anchorpoint">troubleshooting</a>.')
            elif "TF400813" in str(e):
                ap.UI().show_error(title='Azure DevOps has issues to create your project', 
                                   duration=8000, 
                                   description=f'Check the <a href="https://dev.azure.com/{current_org}/_settings/organizationPolicy">policies</a>if Third-party application access via OAuth is enabled. If enabled, please check our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#member-cannot-create-azure-devops-projects-from-anchorpoint">troubleshooting</a> or try again.')
            elif "TF50316" in str(e):
                # Extract the name from the exception message
                match = re.search(r'The following name is not valid: (.*). Please', str(e))
                if match:
                    invalid_name = match.group(1)
                    ap.UI().show_error(
                        title='Cannot create Azure DevOps Project',
                        duration=8000,
                        description=f'Failed to create, because the already adjusted project name "{invalid_name}" does not conform to the Azure DevOps <a href="https://learn.microsoft.com/en-us/azure/devops/organizations/settings/naming-restrictions?view=azure-devops#azure-repos-git">naming restrictions</a>. Please try again with a different name.'
                    )
                else:
                    ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                       duration=8000, 
                                       description=f'Failed to create, because project name does not conform to the Azure DevOps <a href="https://learn.microsoft.com/en-us/azure/devops/organizations/settings/naming-restrictions?view=azure-devops#azure-repos-git">naming restrictions</a>. Please try again with a different name.')
            elif "TF50309" in str(e):
                ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                   duration=8000, 
                                   description=f'Failed to create, because you do not have permission to create projects in the {current_org} organization. Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#member-cannot-create-azure-devops-projects-from-anchorpoint">troubleshooting</a>.')
            elif "project already exists" in str(e):
                ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                   duration=8000, 
                                   description=f'Failed to create, because project with name {project_name} already exists. Please try again.')
            elif "Connection aborted" in str(e):
                ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                   duration=8000, 
                                   description=f'Failed to create, because the connection was aborted. Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#member-cannot-create-azure-devops-projects-from-anchorpoint">troubleshooting</a>.')
            else:
                ap.UI().show_error(title='Cannot create Azure DevOps Project', 
                                   duration=8000, 
                                   description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#member-cannot-create-azure-devops-projects-from-anchorpoint">troubleshooting</a>.')
            raise e