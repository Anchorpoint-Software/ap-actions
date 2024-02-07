import anchorpoint as ap
import apsync as aps
import webbrowser
from gitea_client import *
import os, re
from urllib.parse import urlparse, urlunparse

integration_tags = ["git", "gitea_self_hosted"]
connect_action_id = "gitea_connect"
disconnect_action_id = "gitea_disconnect"
reconnect_action_id = "gitea_reconnect"
setup_action_id = "gitea_setup"
settings_action_id = "gitea_settings"
clear_action_id = "gitea_clear"
settings_org_dropdown_entry = "org_dropdown"
settings_credential_btn_entry = "credential_btn"
settings_credential_btn_highlight_entry = "credential_btn_highlight"
create_repo_dialog_entry = "gitea_create_repo"
repo_dropdown_entry = "gitea_repository_dropdown"
create_dialog_info_entry = "gitea_create_dialog_info"
integration_project_name_key = "project_name"

server_url_entry = "server_url"
client_id_entry = "client_id"
client_secret_entry = "client_secret"
client_values_info_entry = "client_values_info"
connect_to_server_btn_entry = "connect_to_server_btn"
remove_data_entry = "remove_data"

def on_load_integrations(integrations, ctx: ap.Context):
    integration = GiteaIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = GiteaClient(ctx.workspace_id)

    if not client.is_setup():
        return
    
    client.setup_workspace_settings()
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot add member to Gitea', duration=6000, description=f'Failed to get current organization. You have to add your member directly on Gitea.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitea', duration=6000, description=f'Failed to connect integration. You have to add your member directly on Gitea.')
        return
    
    try:
        client.add_user_to_organization(current_org, email)
        ap.UI().show_success(title='Member added to Gitea', duration=3000, description=f'User {email} added to organization {current_org.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot add member to Gitea', duration=10000, description=f'Cannot to add the member to the organization. You have to add your member <a href="{client.get_host_url()}/org/{current_org.name}/teams/owners">directly on Gitea</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = GiteaClient(ctx.workspace_id)

    if not client.is_setup():
        return
    
    client.setup_workspace_settings()
    current_org = client.get_current_organization()
    if current_org is None:
        ap.UI().show_error(title='Cannot remove member to Gitea', duration=6000, description=f'Cannot get current organization. You have to remove your member directly on Gitea.')
        return
    
    if current_org.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot remove member to Gitea', duration=6000, description=f'Failed to connect integration. You have to remove your member directly on Gitea.')
        return
    
    try:
        client.remove_user_from_organization(current_org, email)
        ap.UI().show_success(title='Member removed from Gitea', duration=3000, description=f'User {email} removed from organization {current_org.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot remove member from Gitea', duration=10000, description=f'Failed to remove member from organization. You have to remove your member <a href="{client.get_host_url()}/org/{current_org.name}/teams/owners">directly on Gitea</a>.')

def open_browser_and_close_dialog(dialog, url):
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
        ap.UI().show_error(title='Cannot add member to Gitea repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GiteaClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add member to Gitea repository', duration=6000, description=f'Gitea integration is not setup. Please add manually.')
        return
    
    client.setup_workspace_settings()
    
    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitea repository', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.add_user_to_repository(current_org, email, project_name)
        ap.UI().show_success(title='Member added to Gitea repository', duration=3000, description=f'User {email} added to repository {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitea_repo_name(project.name)

        import time
        time.sleep(1)
        dialog = ap.Dialog()
        dialog.title = "Cannot add member to Gitea repository"
        dialog.icon = ":/icons/organizations-and-products/gitea.svg"
        dialog.add_info(f'You have to add your member directly on Gitea.')
        dialog.add_button("Add Member on Gitea", callback=lambda d: open_browser_and_close_dialog(d, f'{client.get_host_url()}/{current_org.name}/{repo_name}/settings/collaboration'))
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
        ap.UI().show_error(title='Cannot remove member from Gitea repository', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GiteaClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove member from Gitea repository', duration=6000, description=f'Gitea integration is not setup. Please add manually.')
        return
    
    client.setup_workspace_settings()

    if not client.init():
        ap.UI().show_error(title='Cannot remove member from Gitea repository', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_org = client.get_current_organization()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.remove_user_from_repository(current_org, email, project_name)
        ap.UI().show_success(title='Member removed from Gitea repository', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitea_repo_name(project.name)
        ap.UI().show_error(title='Cannot remove member from Gitea repository', duration=10000, description=f'Failed to remove member, because "{str(e)}". You have to remove your member <a href="{client.get_host_url()}/{current_org.name}/{repo_name}/settings/collaboration">directly on Gitea</a>.')
        return

def setup_credentials_async(dialog, host_url: str):
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    try:
        dialog.set_processing(settings_credential_btn_highlight_entry, True, "Updating")
        dialog.set_processing(settings_credential_btn_entry, True, "Updating")

        parsed_url = urlparse(host_url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path if parsed_url.path != '' else None

        GitRepository.erase_credentials(netloc, scheme, path)
        result = GitRepository.get_credentials(netloc, scheme, path)
        if (result is None or result.get("host") is None or result["host"] != netloc 
            or result.get("username") is None or result.get("password") is None):
            raise Exception("Login failed")
        GitRepository.store_credentials(netloc, scheme, result["username"], result["password"], path)
        ap.UI().show_success(title='Gitea credentials stored', duration=3000, description=f'Gitea credentials stored successfully.')
    except Exception as e:
        ap.UI().show_error(title='Cannot store Gitea credentials', duration=6000, description=f'Failed to store credentials, because "{str(e)}". Please try again.')
    finally:
        dialog.set_processing(settings_credential_btn_highlight_entry, False)
        dialog.set_processing(settings_credential_btn_entry, False)
        if script_dir in sys.path:
            sys.path.remove(script_dir)

class GiteaIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        self.client = GiteaClient(ctx.workspace_id)

        self.name = 'Gitea (self-hosted)'
        self.description = "A self-hosted Git repository for local or cloud servers. Create repositories <br> and add members directly from Anchorpoint. <a href='https://docs.anchorpoint.app/docs/1-overview/integrations/gitea/'>Learn more</a>"
        self.priority = 96
        self.tags = integration_tags

        icon_path = os.path.join(ctx.yaml_dir, "gitea/logo.svg")
        self.dashboard_icon = icon_path
        self.preferences_icon = icon_path
        self.is_setup = self.client.is_setup()
        self.is_setup_for_workspace = self.client.is_setup_for_workspace()

        if self.is_setup:
            self.client.setup_workspace_settings()
            if self.client.setup_refresh_token():
                self._setup_connected_state()
            else:
                self._setup_reconnect_state()
        else:
            self._setup_not_connected_state()

        createRepo = ap.IntegrationAction()
        createRepo.name = "New Gitea Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/gitea.svg")
        self.add_create_project_action(createRepo)

    def _setup_not_connected_state(self):
        self.clear_preferences_actions()

        connect = ap.IntegrationAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to Gitea"
        self.add_preferences_action(connect)

        if(self.is_setup_for_workspace):
            disconnect = ap.IntegrationAction()
            disconnect.name = "Clear"
            disconnect.enabled = True
            disconnect.icon = aps.Icon(":/icons/clearCache.svg")
            disconnect.identifier = disconnect_action_id
            disconnect.tooltip = "Clear Gitea configuration"
            self.add_preferences_action(disconnect)
        self.is_connected = False

    def _setup_connected_state(self):
        self.clear_preferences_actions()

        disconnect = ap.IntegrationAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Clear Gitea configuration"
        self.add_preferences_action(disconnect)

        settings = ap.IntegrationAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for Gitea integration"
        self.add_preferences_action(settings)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.clear_preferences_actions()

        reconnect = ap.IntegrationAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to Gitea"
        self.add_preferences_action(reconnect)

        if(self.is_setup_for_workspace):
            disconnect = ap.IntegrationAction()
            disconnect.name = "Clear"
            disconnect.enabled = True
            disconnect.icon = aps.Icon(":/icons/clearCache.svg")
            disconnect.identifier = disconnect_action_id
            disconnect.tooltip = "Clear Gitea configuration"
            self.add_preferences_action(disconnect)

        self.is_connected = False
    
    def execute_preferences_action(self, action_id: str):
        if action_id == connect_action_id:
            if not self.client.is_setup_for_workspace():
                self.show_workspace_setup_dialog()
            else:
                self.client.setup_workspace_settings()
                self.client.start_auth()
                self.start_auth()
        elif action_id == disconnect_action_id:
            self.show_clear_integration_dialog()
        elif action_id == reconnect_action_id:
            if not self.client.is_setup_for_workspace():
                self.show_workspace_setup_dialog()
            else:
                self.client.setup_workspace_settings()
                self.client.start_auth()
                self.start_auth()
        elif action_id == settings_action_id:
            try:
                orgs = self.client.get_organizations()
                if not orgs:
                    raise Exception("Failed to load organizations")
                current_org = self.client.get_current_organization()
                if current_org is None:
                    current_org = orgs[0]
                    self.client.set_current_organization(current_org)
                self.show_settings_dialog(current_org, orgs)
            except Exception as e:
                ap.UI().show_error(title='Cannot load Gitea Settings', duration=6000, description=f'Failed to load, because "{str(e)}". Please try again.')
                return

    def on_auth_deeplink_received(self, url: str):
        try:
            self.client.oauth2_response(response_url=url)
            orgs = self.client.get_organizations()
            if not orgs:
                raise Exception("Failed to load organizations")
            current_org = self.client.get_current_organization()
            if current_org is None:
                current_org = orgs[0]
                self.client.set_current_organization(current_org)            
            self.show_settings_dialog(current_org, orgs)
            self._setup_connected_state()
            self.is_setup = True
            self.is_setup_for_workspace = True
            self.is_connected = True
            self.start_update()
        except Exception as e:
            ap.UI().show_error(title='Gitea authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            if self.is_setup:
                dialog.add_info("You may need to <b>log into</b> Gitea again after the final step.", var=create_dialog_info_entry)
                return [create_dialog_info_entry]
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_id: str, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_id, project_name, progress)
        
    def validate_url(self, dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please insert a valid url"

        url_pattern = re.compile(
            r'^(https?://)'  # scheme (http:// or https://)
            r'([a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})+|localhost)'  # Domain name or IP address
            r'(:\d+)?'  # Optional port number
            r'(/.*)?$'  # Optional path with a trailing slash
        )
        
        # Use the pattern to match the URL
        if url_pattern.match(value) == None:
            dialog.set_value(client_values_info_entry, "Please insert your valid Gitea url first.")
            return "Please insert a valid url"
        extracted_url = self.extract_server_url(value)
        dialog.set_value(client_values_info_entry, f"Create a <a href='{extracted_url}/admin/applications'>Gitea OAuth app</a> with following settings:<br><br>1. Application Name: <b>Anchorpoint</b><br>2. Redirect URI: <b>https://www.anchorpoint.app/app/integration/auth</b><br>3. Check <b>Confidential Client</b> checkbox <br> 4. Press <b> Create Application</b> and enter the client keys below")
        return
        
    def extract_server_url(self, url: str):
        parsed_url = urlparse(url)
        return urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        
    def update_dialog_after_validate(self, dialog: ap.Dialog, isValid: bool):
        dialog.set_enabled(connect_to_server_btn_entry, isValid)

    def validate_client_id(self, dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please add a valid client id"
        
        import re
        client_id_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        if client_id_pattern.match(value) == None:
            return "Please add a client id with pattern xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        return
    
    def validate_client_secret(self, dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please add a valid client secret"

        import re
        pattern = re.compile(r'^gto_[0-9a-zA-Z]{52}$')
        if pattern.match(value) is None:
            return "Please add a client secret with pattern gto_\{52 chararacters\}"
        return
    
    # def connect_to_server(self, dialog: ap.Dialog, ctx):
        
    #     ctx.run_async(self.connect_to_server_async, dialog)

    def connect_to_server(self, dialog: ap.Dialog):
        dialog.set_processing(connect_to_server_btn_entry, True, "Testing connection")
        server_url = dialog.get_value(server_url_entry)
        client_id = dialog.get_value(client_id_entry)
        client_secret = dialog.get_value(client_secret_entry)
        reachable = self.client.is_server_reachable(server_url)
        dialog.set_processing(connect_to_server_btn_entry, False)
        if reachable:
            self.client.store_for_workspace(host_url=server_url, client_id=client_id, client_secret=client_secret)
            self.client.setup_workspace_settings()
            ap.UI().show_success(title='Connected to Gitea', duration=3000, description=f'You are now connected to Gitea.<br>Please continue with the authentication.')
            self.client.start_auth()
            self.start_auth()
            dialog.close()
        else:
            ap.UI().show_error(title='Cannot connect to Gitea', duration=6000, description=f'Failed to connect to Gitea.<br>Please check your url and try again.')
            dialog.set_enabled(connect_to_server_btn_entry, False)
            return

    def show_workspace_setup_dialog(self):
        dialog = ap.Dialog()
        dialog.name = setup_action_id
        dialog.title = "Setup Gitea for Workspace"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitea/logo.svg")
        dialog.callback_validate_finsihed = self.update_dialog_after_validate

        dialog.add_text("<b>1. Gitea URL</b>", var="remoteurltext")
        dialog.add_info("Enter your Gitea server url with port if needed")
        dialog.add_input(placeholder='https://mygiteaserver.com:3030', var=server_url_entry, width=400, validate_callback=self.validate_url)

        dialog.add_text("<b>2. Gitea OAuth Application</b>", var="oauthapp")
        dialog.add_info("Insert your valid Gitea url first", var=client_values_info_entry)
        dialog.add_text("Client ID")
        dialog.add_input(placeholder='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', var=client_id_entry, width=400, validate_callback=self.validate_client_id)
        dialog.add_text("Client Secret")
        dialog.add_info("This key must have 56 characters")
        dialog.add_input(placeholder='gto_876s8df768768768769sfg68f76g8...', var=client_secret_entry, width=400, validate_callback=self.validate_client_secret)

        dialog.add_button("Connect to Gitea", var=connect_to_server_btn_entry, callback=lambda d: self.connect_to_server(d), enabled=False)

        dialog.show()

    def change_org_callback(self, dialog: ap.Dialog, value: str, orgs):
        org = next((x for x in orgs if x.name == value), None)
        if org is None:
            return
        self.client.set_current_organization(org)

    def credential_btn_callback(self, dialog: ap.Dialog):
        dialog.hide_row(settings_credential_btn_entry, False)
        dialog.hide_row(settings_credential_btn_highlight_entry, True)
        ctx = ap.get_context()
        ctx.run_async(setup_credentials_async, dialog, self.client.get_host_url())

    def show_settings_dialog(self, current_org, orgs):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Gitea Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitea/logo.svg")

        dialog.add_text("<b>1. Account</b>", var="accounttext")
        dialog.add_text(orgs[0].name)
        dialog.add_empty()

        dialog.add_text("<b>2. Organization</b>", var="orgtext")

        dropdown_entries = []
        for org in orgs:
            entry = ap.DropdownEntry()
            entry.name = org.name
            if org.avatar_url is not None:
                entry.icon = org.avatar_url
            else:
                entry.icon = ":/icons/organizations-and-products/gitea.svg"
            entry.use_icon_color = True
            dropdown_entries.append(entry)

        dialog.add_dropdown(current_org.name, dropdown_entries, var=settings_org_dropdown_entry, callback=lambda d, v: self.change_org_callback(d,v, orgs))
        dialog.add_info("Allow Anchorpoint to create repositories and add<br>members in a organization.")
        dialog.add_empty()

        dialog.add_text("<b>3. Git Credentials</b>")
        dialog.add_image(os.path.join(self.ctx.yaml_dir, "gitea/giteaCredentials.webp"),width=230)
        dialog.add_info("Opens the Git Credential Manager, where you need to<br>enter your Gitea login data to grant Anchorpoint<br>permission to upload and download files.")
        dialog.add_button("Enter your Gitea credentials", var=settings_credential_btn_highlight_entry, callback=self.credential_btn_callback)
        dialog.add_button("Enter your Gitea credentials", var=settings_credential_btn_entry, callback=self.credential_btn_callback, primary=False)
        dialog.hide_row(settings_credential_btn_entry, True)

        dialog.show()

    def show_clear_integration_dialog(self):
        dialog = ap.Dialog()
        dialog.name = clear_action_id
        dialog.title = "Disconnect Gitea"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitea/logo.svg")

        dialog.add_text("Do you also want to remove the gitea server infos (url,<br>client id and client secret) for all workspace members?")
        dialog.add_checkbox(text="Delete gitea server infos from workspace",var=remove_data_entry, default=False)

        dialog.add_button("Disconnect", var="disconnect", callback=self.clear_integration)
        dialog.show()

    def clear_integration(self, dialog: ap.Dialog):
        remove_data = dialog.get_value(remove_data_entry)
        self.client.clear_integration(remove_data)
        self.is_setup = False
        self.is_setup_for_workspace = False
        self._setup_not_connected_state()
        self.start_update()
        dialog.close()

    def create_new_repo(self, project_id: str,  project_name: str, progress: ap.Progress) -> str:
        current_org = self.client.get_current_organization()
        try:
            progress.set_text("Creating Gitea Project")
            new_repo = self.client.create_project(current_org, project_name)
            settings = aps.SharedSettings(project_id, self.ctx.workspace_id, "integration_info")
            settings.set(integration_project_name_key, new_repo.name)
            settings.store()

            progress.set_text("")
            if new_repo is None:
                raise Exception("Created project not found")
            return new_repo.clone_url
        except Exception as e:
            if "already exists" in str(e):
                ap.UI().show_error(title='Cannot create Gitea Repository', duration=8000, description=f'Failed to create, because project with name {project_name} already exists. Please try again.')
            else:
                ap.UI().show_error(title='Cannot create Gitea Repository', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/1-overview/integrations/gitea">troubleshooting</a>.')
            raise e