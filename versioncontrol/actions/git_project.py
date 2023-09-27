import anchorpoint as ap
import apsync as aps
import os, sys, platform

create_project_dropdown = "create_project_dropdown"
remote_dropdown_entry_name = "Connect via Https"
no_remote_dropdown_entry_name = "No Remote"
remote_entry_url_input = "remote_entry_url_input"
setup_integration_btn = "setup_integration_btn"
remote_entry_login_info_text= "remote_entry_login_info_text"

def validate_path(dialog: ap.Dialog, value):
    if not value or len(value) == 0:
        return "Please add a folder for your project files"
    if not os.path.exists(value):
        return "Please add a real folder"
    else:
        return

def validate_url(dialog: ap.Dialog, value):
    if not value or len(value) == 0:
        return "Please add a link to a remote Git repository"
    else:
        return
    
def validate_dropdown(dialog: ap.Dialog, value, setup_integration_visible):
    if setup_integration_visible:
        return "Please setup integration"
    else:
        return
    
def get_repo_url(git, path):
    try:
        repo = git.GitRepository.load(path)
        if repo:
            return repo.get_remote_url()
        return None
    except:
        return None
    
def url_changed(dialog: ap.Dialog, value):
    git_provider = "your Git Server"
    if "dev.azure" in value:
        git_provider = "Azure DevOps"
    elif "visualstudio" in value:
        git_provider = "Azure DevOps"
    elif "github" in value:
        git_provider = "GitHub"
    elif "gitlab" in value:
        git_provider = "GitLab"
    elif "bitbucket" in value:
        git_provider = "Bitbucket"
        
    dialog.set_value(remote_entry_login_info_text, f"You eventually need to <b>log into</b> {git_provider} after the final step")

def path_changed(dialog: ap.Dialog, git, path, ctx):
    from add_ignore_config import get_ignore_file_dropdown_entries, get_ignore_file_default, NO_IGNORE
    dropdown_values = get_ignore_file_dropdown_entries(ctx.yaml_dir)
    ignore_default = get_ignore_file_default(dropdown_values, path)
    if not ignore_default:
        dialog.set_value("ignore_dropdown", NO_IGNORE)
    else:
        dialog.set_value("ignore_dropdown", ignore_default)
    url = get_repo_url(git, path)
    if url and url != "":
        dialog.set_value("url", url)
    

def add_git_ignore(repo, context, project_path, ignore_value = None):
    script_dir = os.path.dirname(__file__)
    sys.path.insert(0, script_dir)
    import add_ignore_config
    if script_dir in sys.path: sys.path.remove(script_dir)
    repo.ignore(".ap/project.json", local_only=True)
    repo.ignore("*.approj", local_only=True)
    if platform.system() == "Darwin":
        repo.ignore(".DS_Store", local_only=True)
    if ignore_value and ignore_value != add_ignore_config.NO_IGNORE:
        add_ignore_config.add_git_ignore(ignore_value, project_path, context.yaml_dir)

def _install_git_async(dialog, git_helper):
    try:
        git_helper.install_git()
        ap.reload_create_project_dialog()
    finally:
        dialog.set_processing("install", False)

def install_git_async(dialog, ctx, path, git_helper):
    dialog.set_processing("install", True, "Installing Git")
    ctx.run_async(_install_git_async, dialog, git_helper)

try:
    class GitProjectType(ap.ProjectType):
        def __init__(self, path: str, ctx: ap.Context, integrations: ap.IntegrationList):
            super().__init__()
            self.context = ctx
            self.path = path
            self.git_integrations = integrations.get_all_for_tags(["git"])

            script_dir = os.path.join(os.path.dirname(__file__), "..")
            sys.path.insert(0, script_dir)

            import git_repository_helper as githelper
            import vc.apgit_utility.install_git as install_git
            if script_dir in sys.path: sys.path.remove(script_dir)

            self.git_installed = install_git.is_git_installed()
            self.dialog = ap.Dialog()
            self.git = None
            self.githelper = githelper
            self.setup_integration_name = None

            if not self.git_installed:
                self.dialog.add_text("To use Anchorpoint with Git repositories you have to install it")
                self.dialog.add_info("When installing Git you are accepting the <a href=\"https://raw.githubusercontent.com/git-for-windows/git/main/COPYING\">license</a> of the owner.")
                self.dialog.add_button("Install", var="install", callback = lambda d: install_git_async(d, self.context, self.path, install_git))
                if "set_valid" in dir(ap.Dialog):
                    self.dialog.set_valid(False)
                return

            try:
                import vc.apgit.repository as git
                self.git = git
            except Warning as e:
                sys.exit(0)

            repo_url = None
            try:
                if self.git and os.path.exists(path) and path != "":
                    repo = self.git.GitRepository.load(path)
                    repo_url = repo.get_remote_url()
            except:
                pass
            
            if not repo_url: repo_url = ""

            path_placeholder = "Z:\\Projects\\ACME_Commercial"
            if platform.system() == "Darwin":
                path_placeholder = "/Projects/ACME_Commercial"            


            self.setup_integration_visible = False
            self.dialog.add_input(var="project_path", default=path, placeholder=path_placeholder, width = 420, browse=ap.BrowseType.Folder, validate_callback=validate_path, callback=lambda d,v: path_changed(d,self.git,v,ctx))

            from add_ignore_config import get_ignore_file_dropdown_entries, NO_IGNORE
            dropdown_values = get_ignore_file_dropdown_entries(ctx.yaml_dir)

            self.dialog.add_text("<b>Template for .gitignore</b>", var="gitignoretext")
            no_entry = ap.DropdownEntry()
            no_entry.name = NO_IGNORE
            no_entry.icon = ":icons/none.svg"
            dropdown_values.insert(0, no_entry)
            self.dialog.add_dropdown(no_entry.name, dropdown_values, var="ignore_dropdown")
            self.dialog.add_info("A <b>gitignore</b> excludes certain files from version control (e.g. <b>Unreal Engine</b>'s build result).")
            self.dialog.add_text("<b>Remote Settings</b>", var="remoteSettings")
            self.create_dropdown_entries(repo_url)
            path_changed(self.dialog, self.git, self.path, ctx)


        def create_dropdown_entries(self, repo_url: str):
            self.create_project_dropdown_entries = []
            self.dialogVarMap = {}

            #create dropdown entries
            if repo_url == "":
                for integration in self.git_integrations:
                    for action in integration.get_create_project_actions():
                        entry = ap.DropdownEntry()
                        entry.name = action.name
                        entry.icon = action.icon.path
                        self.create_project_dropdown_entries.append(entry)

            remote_entry = ap.DropdownEntry()
            remote_entry.name = remote_dropdown_entry_name
            remote_entry.icon = ":icons/Misc/git.svg"
            self.create_project_dropdown_entries.append(remote_entry)

            if repo_url == "":
                local_entry = ap.DropdownEntry()
                local_entry.name = no_remote_dropdown_entry_name
                local_entry.icon = ":icons/desktop.svg"
                self.create_project_dropdown_entries.append(local_entry)
                self.dialogVarMap[local_entry.name] = []

            self.setup_integration_visible = False
            self.dialog.add_dropdown(self.create_project_dropdown_entries[0].name, self.create_project_dropdown_entries, var=create_project_dropdown, callback = self.on_dropdown_change, validate_callback=lambda d,v: validate_dropdown(d,v,self.setup_integration_visible))

            #create dialog entries for each dropdown entry
            if repo_url == "":
                for integration in self.git_integrations:
                    for action in integration.get_create_project_actions():
                        self.dialogVarMap[action.name] = integration.setup_create_project_dialog_entries(action.identifier, self.dialog)

            self.dialog.add_info("You may need to <b>log into</b> your Git server after the final step.", var=remote_entry_login_info_text)
            self.dialog.add_input(default=repo_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var=remote_entry_url_input, width = 525, validate_callback=validate_url, callback=url_changed)
            self.dialog.add_button("Setup Integration", var=setup_integration_btn, callback=self.on_setup_integration_btn_clicked, primary=True)

            self.dialog.hide_row(setup_integration_btn,True)
            self.dialogVarMap[remote_entry.name] = [remote_entry_url_input, remote_entry_login_info_text]
            if repo_url == "":
                self.toggle_row_visibility(self.dialog,self.create_project_dropdown_entries[0].name)
                self.dialog.set_value(create_project_dropdown, self.create_project_dropdown_entries[0].name)
                self.on_dropdown_change(self.dialog, self.create_project_dropdown_entries[0].name)
            else:
                self.dialog.set_value(remote_entry_url_input, repo_url)
                self.toggle_row_visibility(self.dialog,remote_dropdown_entry_name)
                self.dialog.set_value(create_project_dropdown, remote_dropdown_entry_name)

        def on_dropdown_change(self, dialog, value):
            self.setup_integration_visible = False
            self.toggle_row_visibility(dialog,value)
            for integration in self.git_integrations:
                action_found = False
                for action in integration.get_create_project_actions():
                    if action.name == value:
                        action_found = True
                        if(not integration.is_setup or not integration.is_connected):
                            dialog.set_value(setup_integration_btn, f"Setup {integration.name} Integration")
                            self.setup_integration_name = integration.name
                            dialog.hide_row(setup_integration_btn,False)
                            self.setup_integration_visible = True
                        else:
                            integration.on_create_project_dialog_entry_selected(action.identifier, dialog)
                        break
                if action_found:
                    break
            if not self.setup_integration_visible:
                dialog.hide_row(setup_integration_btn,True)

        def toggle_row_visibility(self, dialog,value):
                row_vars = self.dialogVarMap[value]
                #show all rows of the selected integration action
                for row_var in row_vars:
                    dialog.hide_row(row_var,False)
                #hide all other rows
                for key, row_vars in self.dialogVarMap.items():
                    if key != value:
                        for row_var in row_vars:
                            dialog.hide_row(row_var,True)

        def remote_changed(self, dialog: ap.Dialog, value):
            for integration in self.git_integrations:
                if not integration.is_setup:
                    if integration.supports_create_project(value):
                        dialog.set_value(setup_integration_btn, f"Setup {integration.name} Integration")
                        self.setup_integration_name = integration.name
                        dialog.hide_row(setup_integration_btn,False)
                        return
            dialog.hide_row(setup_integration_btn,True)

        def on_setup_integration_btn_clicked(self, dialog: ap.Dialog):
            if not self.setup_integration_name: return
            for integration in self.git_integrations:
                if integration.name == self.setup_integration_name:
                    ap.open_integration_preferences(integration.name)
                    break

        def get_project_name_candidate(self):
            return os.path.basename(self.get_project_path())

        def get_project_path(self):
            return self.dialog.get_value("project_path")
        
        def get_dialog(self):         
            return self.dialog

        def setup_project(self, project_id: str, progress):
            self.project = aps.get_project_by_id(project_id, self.context.workspace_id)

            project_path = self.dialog.get_value("project_path")
            git_ignore = self.dialog.get_value("ignore_dropdown")
            self.path = project_path

            action_id = self.dialog.get_value("create_project_dropdown")

            remote_enabled = False
            repo_url = ""
            integration_tags = None

            if action_id == remote_dropdown_entry_name:
                repo_url = self.dialog.get_value(remote_entry_url_input)
                remote_enabled = True
            elif action_id == no_remote_dropdown_entry_name:
                remote_enabled = False
            else:
                for integration in self.git_integrations:
                    for action in integration.get_create_project_actions():
                        if action.name == action_id:
                            repo_url = integration.setup_project(action.identifier, self.dialog, self.project.name, progress)
                            integration_tags = integration.tags
                            remote_enabled = True
                            break

            folder_is_empty = self.githelper.folder_empty(project_path)
            git_parent_dir = self._get_git_parent_dir(project_path)

            if integration_tags != None:
                settings = aps.SharedSettings(project_id, self.context.workspace_id, "integration_info")
                settings.set("integration_tags", ";".join(integration_tags))
                settings.store()

            if folder_is_empty and remote_enabled:
                # Case 1: Empty Folder & Remote URL -> Clone
                self._clone(repo_url, project_path, self.project, git_ignore, progress)
                return

            if not git_parent_dir:
                # Case 2: Folder with no Repo -> Create new Repo
                url = repo_url if remote_enabled else None
                self._init_repo(url, project_path, self.project, git_ignore, progress)
                return

            if self._is_path_equal(git_parent_dir, project_path):
                # Case 3: Folder Contains Git in root -> Open Repo
                self._open_repo(project_path, self.project, git_ignore)
                return

            if git_parent_dir != None and not self._is_path_equal(git_parent_dir, project_path):
                # Case 4: Folder Contains Git in Subdir -> Error
                ap.UI().show_error("Could not setup project", "Found a Git repository in a subfolder, this is currently not supported: {git_parent_dir}", duration=10000)
                sys.exit(0)

            print(f"project_path {project_path}")
            print(f"git_ignore {git_ignore}")   
            print(f"remote_enabled {remote_enabled}")
            print(f"repo_url {repo_url}")
            print(f"folder_is_empty {folder_is_empty}")
            print(f"git_parent_dir {git_parent_dir}")

            raise Exception(f"Cannot create the Git project, unknown set of parameters")

        def project_created(self):
            folder_id = aps.get_folder_id(self.path)
            channel = aps.get_timeline_channel(self.project, "Git")
            if channel:
                metadata = channel.metadata
                metadata["gitPathId"] = folder_id
                channel.metadata = metadata
                aps.update_timeline_channel(self.project, channel)
                        
            aps.set_folder_icon(self.path, aps.Icon(":/icons/versioncontrol.svg", "#f3d582"))

        def _get_branch_names(self, repo):
            branches = repo.get_branches()
            names = []
            for branch in branches:
                names.append(branch.name)

            return names
        
        def _init_repo(self, url, project_path, project, git_ignore, progress):
            repo = self.git.GitRepository.create(project_path, self.context.username, self.context.email)
            self.githelper.update_project(project_path, url, False, None, project)
            if url:
                repo.add_remote(url)
                repo.fetch(progress=self.githelper.FetchProgress(progress))
                branches = self._get_branch_names(repo)
                if len(branches) > 0:
                    ap.UI().show_error("Could not setup project", "You need to pick an empty folder because the remote repository already contains files.", duration=10000)
                    sys.exit(0)

            self._add_git_ignore(repo, git_ignore, project_path)
            return repo
        
        def _open_repo(self, project_path, project, git_ignore):
            repo = self.git.GitRepository.load(project_path)

            url = repo.get_remote_url()
            if url == "": url = None

            repo.set_username(self.context.username, self.context.email, project_path)
            self.githelper.update_project(project_path, url, False, None, project)
            self._add_git_ignore(repo, git_ignore, project_path)

            if url and repo.get_remote_url() != url:
                try:
                    repo.add_remote(url)
                    repo.set_upstream("main")
                except:
                    pass
                

        def _clone(self, url, project_path, project, git_ignore, progress):
            try:
                repo = self.git.GitRepository.clone(url, project_path, self.context.username, self.context.email, progress=self.githelper.CloneProgress(progress))
                progress.finish()
            
                self.githelper.update_project(project_path, url, False, None, project, True)
                self._add_git_ignore(repo, git_ignore, project_path)
            except Exception as e:            
                print(e)
                ap.UI().show_error("Could not setup project", "You might have entered a wrong username / password, or you don't have access to the repository.", duration=10000)
                sys.exit(0)

        def _add_git_ignore(self, repo, ignore_value, project_path):
            add_git_ignore(repo, self.context, project_path, ignore_value)

        def _get_git_parent_dir(self, folder_path):
            for root, dirs, _ in os.walk(folder_path):
                for dir in dirs:
                    if dir == ".git":
                        return root
            return None

        def _is_path_equal(self, path1: str, path2: str):
            if path1 == None or path2 == None: return False
            
            norm1 = os.path.normpath(os.path.normcase(path1))
            norm2 = os.path.normpath(os.path.normcase(path2))
            return norm1 == norm2

    def on_show_create_project(project_types, integrations, path: str, ctx: ap.Context):
        import os
        iconPath = os.path.join(ctx.yaml_dir, "icons/project_type_git.svg")
        gitProjectType = GitProjectType(path, ctx, integrations)
        gitProjectType.name = 'Git Repository'
        gitProjectType.description = 'Open or create a Git repository for your <font color=#FFFFFF>Unreal</font> or <font color=#FFFFFF>Unity</font> project. Connect it to Git providers such as GitHub, Azure Devops or self-hosted Git servers.'
        gitProjectType.priority = 100
        gitProjectType.pre_selected = False
        if path:
            git_path = os.path.join(path, ".git")
            gitProjectType.pre_selected = os.path.exists(git_path)
        
        gitProjectType.icon = iconPath
        project_types.add(gitProjectType)

    
except AttributeError as e:
    if aps.get_api_version() <= aps.ApiVersion("1.5.0"):
        pass
    else:
        raise e

def connect_repo(dialog: ap.Dialog, path):
    dialog.close()
    if "show_create_project_dialog" in dir(ap):
        ap.show_create_project_dialog(path)

def update_open_settings(dialog: ap.Dialog, value, path):
    settings = aps.Settings("connect_git_repo")
    settings.set(path, value)
    settings.store()

def on_folder_opened(ctx: ap.Context):
    path = ctx.path
    git_dir = os.path.join(path, ".git")
    if not os.path.exists(git_dir):
        return

    if len(ctx.project_id) > 0:
        return

    settings = aps.Settings("connect_git_repo")
    never_ask_again = settings.get(path, False)
    if never_ask_again: 
        return

    dialog = ap.Dialog()
    dialog.title = "Open Git Repository"
    dialog.icon = ctx.icon

    dialog.add_info("Opening a Git repository as a project in Anchorpoint enables <br> certain actions in the project timeline. Learn more about <a href=\"https://docs.anchorpoint.app/docs/4-Collaboration/5-Workflow-Git/\">Git.</a>")
    dialog.add_checkbox(callback=lambda d,v: update_open_settings(d,v,path), var="neveraskagain").add_text("Never ask again")
    dialog.add_button("Continue", var="yes", callback=lambda d: connect_repo(d,path)).add_button("Cancel", callback=lambda d: d.close(), primary=False)
    
    dialog.show()