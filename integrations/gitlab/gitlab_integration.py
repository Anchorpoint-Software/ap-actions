import anchorpoint as ap
import apsync as aps
from gitlab_client import *
import os

integration_tags = ["git", "gitlab"]
gitlab_root = "gitlab.com"
connect_action_id = "gitlab_connect"
disconnect_action_id = "gitlab_disconnect"
reconnect_action_id = "gitlab_reconnect"
settings_action_id = "gitlab_settings"
settings_group_dropdown_entry = "group_dropdown"
settings_credential_btn_entry = "credential_btn"
settings_credential_btn_highlight_entry = "credential_btn_highlight"
create_repo_dialog_entry = "gitlab_create_repo"
repo_dropdown_entry = "gitlab_repository_dropdown"
create_dialog_info_entry = "gitlab_create_dialog_info"

def on_load_integrations(integrations, ctx: ap.Context):
    integration = GitlabIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = GitlabClient(ctx.workspace_id, ap.get_config().gitlab_client_id, ap.get_config().gitlab_client_key)

    if not client.is_setup():
        return
    
    current_group = client.get_current_group()
    if current_group is None:
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=6000, description=f'Failed to get current group. You have to add your member directly on GitLab.')
        return
    
    if current_group.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=6000, description=f'Failed to connect integration. You have to add your member directly on GitLab.')
        return
    
    try:
        client.add_user_to_group(current_group, email)
        ap.UI().show_success(title='Member added to Gitlab', duration=3000, description=f'User {email} added to group {current_group.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=10000, description=f'Cannot to add the member to the group. You have to add your member <a href="https://gitlab.com/groups/{current_group.path}/-/group_members">directly on GitLab</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = GitlabClient(ctx.workspace_id, ap.get_config().gitlab_client_id, ap.get_config().gitlab_client_key)

    if not client.is_setup():
        return
    
    current_group = client.get_current_group()
    if current_group is None:
        ap.UI().show_error(title='Cannot remove member to Gitlab', duration=6000, description=f'Cannot get current group. You have to remove your member directly on GitLab.')
        return
    
    if current_group.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot remove member to Gitlab', duration=6000, description=f'Failed to connect integration. You have to remove your member directly on GitLab.')
        return
    
    try:
        client.remove_user_from_group(current_group, email)
        ap.UI().show_success(title='Member removed from Gitlab', duration=3000, description=f'User {email} removed from group {current_group.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot remove member from Gitlab', duration=10000, description=f'Failed to remove member from group. You have to remove your member <a href="https://gitlab.com/groups/{current_group.path}/-/group_members">directly on GitLab</a>.')

def on_add_user_to_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitlabClient(ctx.workspace_id, ap.get_config().gitlab_client_id, ap.get_config().gitlab_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Gitlab integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_group = client.get_current_group()

    try:
        client.add_user_to_project(current_group, email, project.name)
        ap.UI().show_success(title='Member added to Gitlab project', duration=3000, description=f'User {email} added to project {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitlab_repo_name(project.name)
        print(str(e))
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=10000, description=f'You have to add your member <a href="https://gitlab.com/{current_group.path}/{repo_name}/-/project_members">directly on GitLab</a>.')
        return
    
def on_remove_user_from_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitlabClient(ctx.workspace_id, ap.get_config().gitlab_client_id, ap.get_config().gitlab_client_key)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Gitlab integration is not setup. Please add manually.')
        return
    
    if not client.init():
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_group = client.get_current_group()

    try:
        client.remove_user_from_project(current_group, email, project.name)
        ap.UI().show_success(title='Member removed from Gitlab project', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitlab_repo_name(project.name)
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=10000, description=f'Failed to remove member, because "{str(e)}". You have to remove your member <a href="https://gitlab.com/{current_group.path}/{repo_name}/-/project_members">directly on GitLab</a>.')
        return

def setup_credentials_async(dialog):
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    try:
        dialog.set_processing(settings_credential_btn_highlight_entry, True, "Updating")
        dialog.set_processing(settings_credential_btn_entry, True, "Updating")
        GitRepository.erase_credentials(gitlab_root, "https")
        result = GitRepository.get_credentials(gitlab_root, "https")
        if (result is None or result.get("host") is None or result["host"] != gitlab_root 
            or result.get("username") is None or result.get("password") is None):
            raise Exception("Login failed")
        GitRepository.store_credentials(gitlab_root, "https", result["username"], result["password"])
        ap.UI().show_success(title='Gitlab credentials stored', duration=3000, description=f'Gitlab credentials stored successfully.')
    except Exception as e:
        ap.UI().show_error(title='Cannot store Gitlab credentials', duration=6000, description=f'Failed to store credentials, because "{str(e)}". Please try again.')
    finally:
        dialog.set_processing(settings_credential_btn_highlight_entry, False)
        dialog.set_processing(settings_credential_btn_entry, False)
        if script_dir in sys.path:
            sys.path.remove(script_dir)

class GitlabIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        config = ap.get_config()
        self.client = GitlabClient(ctx.workspace_id, config.gitlab_client_id, config.gitlab_client_key)

        self.name = 'Gitlab (gitlab.com)'
        self.description = "Create repositories, add members and do it all directly in Anchorpoint.<br>Each member will need an Gitlab (gitlab.com) account. <a href='https://docs.anchorpoint.app/docs/1-overview/integrations/gitlab/'>Learn more</a>"
        self.priority = 98
        self.tags = integration_tags

        icon_path = os.path.join(ctx.yaml_dir, "gitlab/logo.svg")
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
        createRepo.name = "New Gitlab Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/gitlab.svg")
        self.add_create_project_action(createRepo)

    def _setup_not_connected_state(self):
        self.clear_preferences_actions()

        connect = ap.IntegrationAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to Gitlab"
        self.add_preferences_action(connect)
        self.is_connected = False

    def _setup_connected_state(self):
        self.clear_preferences_actions()

        disconnect = ap.IntegrationAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Disconnect from Gitlab"
        self.add_preferences_action(disconnect)

        settings = ap.IntegrationAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for Gitlab integration"
        self.add_preferences_action(settings)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.clear_preferences_actions()

        reconnect = ap.IntegrationAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to Gitlab"
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
                groups = self.client.get_groups()
                if not groups:
                    raise Exception("Failed to load groups")
                current_group = self.client.get_current_group()
                if current_group is None:
                    current_group = groups[0]
                    self.client.set_current_group(current_group)
                self.show_settings_dialog(current_group, groups)
            except Exception as e:
                ap.UI().show_error(title='Cannot load Gitlab Settings', duration=6000, description=f'Failed to load, because "{str(e)}". Please try again.')
                return

    def on_auth_deeplink_received(self, url: str):
        try:
            self.client.oauth2_response(response_url=url)
            groups = self.client.get_groups()
            if not groups:
                raise Exception("Failed to load groups")
            current_group = self.client.get_current_group()
            if current_group is None:
                current_group = groups[0]
                self.client.set_current_group(current_group)
            if len(groups) > 1:
                self.show_settings_dialog(current_group, groups)
            self._setup_connected_state()
            self.is_setup = True
            self.is_connected = True
            self.start_update()
        except Exception as e:
            ap.UI().show_error(title='Gitlab authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return
        
    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            if self.is_setup:
                dialog.add_info("You may need to <b>log into</b> Gitlab again after the final step.", var=create_dialog_info_entry)
                return [create_dialog_info_entry]
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_name, progress)

    def change_group_callback(self, dialog: ap.Dialog, value: str, groups):
        group = next((x for x in groups if x.name == value), None)
        if group is None:
            return
        self.client.set_current_group(group)

    def credential_btn_callback(self, dialog: ap.Dialog):
        dialog.hide_row(settings_credential_btn_entry, False)
        dialog.hide_row(settings_credential_btn_highlight_entry, True)
        ctx = ap.get_context()
        ctx.run_async(setup_credentials_async, dialog)

    def show_settings_dialog(self, current_group, groups):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Gitlab Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitlab/logo.svg")

        dialog.add_text("<b>1. Account</b>", var="accounttext")
        dialog.add_text(groups[0].name)
        dialog.add_empty()

        dialog.add_text("<b>2. Group</b>", var="grouptext")

        dropdown_entries = []
        for group in groups:
            entry = ap.DropdownEntry()
            entry.name = group.name
            if group.avatar_url is not None:
                entry.icon = group.avatar_url
            else:
                entry.icon = ":/icons/organizations-and-products/gitlab.svg"
            entry.use_icon_color = True
            dropdown_entries.append(entry)

        dialog.add_dropdown(current_group.name, dropdown_entries, var=settings_group_dropdown_entry, callback=lambda d, v: self.change_group_callback(d,v, groups))
        dialog.add_info("Allow Anchorpoint to create repositories and add<br>members in a dedicated group.")
        dialog.add_empty()

        dialog.add_text("<b>3. Git Credentials</b>")
        dialog.add_image(os.path.join(self.ctx.yaml_dir, "gitlab/gitLabCredentials.webp"),width=230)
        dialog.add_info("Opens the Git Credential Manager, where you need to<br>enter your Gitlab login data to grant Anchorpoint<br>permission to upload and download files.")
        dialog.add_button("Enter your Gitlab credentials", var=settings_credential_btn_highlight_entry, callback=self.credential_btn_callback)
        dialog.add_button("Enter your Gitlab credentials", var=settings_credential_btn_entry, callback=self.credential_btn_callback, primary=False)
        dialog.hide_row(settings_credential_btn_entry, True)

        dialog.show()

    def create_new_repo(self, project_name: str, progress: ap.Progress) -> str:
        current_group = self.client.get_current_group()
        try:
            progress.set_text("Creating Gitlab Project")
            new_repo = self.client.create_project(current_group, project_name)
            progress.set_text("")
            if new_repo is None:
                raise Exception("Created project not found")
            return new_repo.http_url_to_repo
        except Exception as e:
            if "already exists" in str(e):
                ap.UI().show_error(title='Cannot create Gitlab Repository', duration=8000, description=f'Failed to create, because project with name {project_name} already exists. Please try again.')
            else:
                ap.UI().show_error(title='Cannot create Gitlab Repository', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/1-overview/integrations/gitlab">troubleshooting</a>.')
            raise e