import anchorpoint as ap
import apsync as aps
import os, sys, platform

script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)

try:
    from vc.apgit.repository import * 
except Warning as e:
    sys.exit(0)

import git_repository_helper as helper
sys.path.remove(script_dir)

def validate_path(dialog: ap.Dialog, value):
    if not value or len(value) == 0:
        return "Path cannot be empty."
    else:
        return

def validate_url(dialog: ap.Dialog, value):
    if not dialog.get_value("remote"): 
        return

    if not value or len(value) == 0:
        return "Url cannot be empty."
    else:
        return

def change_remote_switch(dialog: ap.Dialog, remote_enabled):
    dialog.hide_row("repotext", not remote_enabled)
    dialog.hide_row("url", not remote_enabled)

class GitProjectType(ap.ProjectType):
    def __init__(self, path: str, ctx: ap.Context):
        super().__init__()
        self.context = ctx
        self.path = path

        repo_url = None
        url_enabled = True
        try:
            if os.path.exists(path) and path != "":
                repo = GitRepository.load(path)
                repo_url = repo.get_remote_url()
                url_enabled = False
        except:
            pass
        
        if not repo_url: repo_url = ""

        path_placeholder = "Z:\\Projects\\ACME_Commercial"
        if platform.system() == "Darwin":
            path_placeholder = "/Projects/ACME_Commercial"            

        self.dialog = ap.Dialog()
        self.dialog.add_input(var="project_path", default=path, placeholder=path_placeholder, width = 420, browse=ap.BrowseType.Folder, validate_callback=validate_path)

        from add_ignore_config import get_ignore_file_types
        dropdown_values = get_ignore_file_types(ctx.yaml_dir)
        dropdown_values.insert(0, "None")
        self.dialog.add_text("GitIgnore Config:").add_dropdown(dropdown_values[0], dropdown_values, var="ignore_dropdown")
        self.dialog.add_info("Add a <b>gitignore</b> to your project to exclude certain files from being committed to Git<br>(e.g. <b>Unreal Engine</b>'s build result).")

        self.dialog.add_switch(True, var="remote", text="Remote Repository", callback=change_remote_switch, enabled=url_enabled)

        self.dialog.add_text("<b>Repository URL</b>", var="repotext")
        self.dialog.add_input(default=repo_url, placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", enabled=url_enabled, var="url", width = 400, validate_callback=validate_url)
        
        self.dialog.add_info("Create a local Git repository or download data from GitHub, for example.")

        settings = aps.Settings("git_project")
        self.dialog.load_settings(settings)

        self.dialog.set_value("project_path", path)
        if repo_url != "":
            self.dialog.set_value("url", repo_url)

        change_remote_switch(self.dialog, self.dialog.get_value("remote"))

    def get_project_name_candidate(self):
        return os.path.basename(self.get_project_path())

    def get_project_path(self):
        print("get project path")
        return self.dialog.get_value("project_path")
    
    def get_dialog(self):         
        return self.dialog

    def setup_project(self, project_id: str, progress) -> bool:
        try:
            project = aps.get_project_by_id(project_id, self.context.workspace_id)
        except Exception as e:
            print(e)
            raise e
        
        project_path = self.dialog.get_value("project_path")
        git_ignore = self.dialog.get_value("ignore_dropdown")
        remote_enabled = self.dialog.get_value("remote")
        repo_url = self.dialog.get_value("url")

        folder_is_empty = self._folder_empty(project_path)
        git_parent_dir = self._get_git_parent_dir(project_path)

        print(f"project_path {project_path}")
        print(f"git_ignore {git_ignore}")
        print(f"remote_enabled {remote_enabled}")
        print(f"repo_url {repo_url}")
        print(f"folder_is_empty {folder_is_empty}")
        print(f"git_parent_dir {git_parent_dir}")
        print("0")

        if folder_is_empty and remote_enabled:
            # Case 1: Empty Folder & Remote URL -> Clone
            print("1")
            self._clone(repo_url, project_path, project, git_ignore, progress)
            return True

        if folder_is_empty and not git_parent_dir:
            # Case 2: Folder with no Repo -> Create new Repo
            print("2")
            url = repo_url if remote_enabled else None
            self._init_repo(url, project_path, project, git_ignore)
            return True

        if self._is_path_equal(git_parent_dir, project_path) and not remote_enabled:
            # Case 3: Folder Contains Git in root & No Remote -> Open Repo
            print("3")
            self._open_repo(None, project_path, project, git_ignore)
            return True

        if self._is_path_equal(git_parent_dir, project_path) and remote_enabled:
            # Case 4: Folder Contains Git in root & Remote -> Open Repo and Connect Upstream
            print("4")
            self._open_repo(repo_url, project_path, project, git_ignore)
            return True

        if git_parent_dir != None and not self._is_path_equal(git_parent_dir, project_path):
            print("5")
            # Case 5: Folder Contains Git in Subdir -> Error
            return False

        print("unknown")

        return False

    def _init_repo(self, url, project_path, project, git_ignore):
        repo = GitRepository.create(project_path, self.context.username, self.context.email)
        helper.update_project(project_path, None, False, None, project)
        self._add_git_ignore(repo, git_ignore, project_path)
        if url:
            repo.add_remote(url)

        return repo
    
    def _open_repo(self, url, project_path, project, git_ignore):
        if url == "": url = None

        repo = GitRepository.load(project_path)
        repo.set_username(self.context.username, self.context.email, project_path)
        helper.update_project(project_path, url, False, None, project)
        self._add_git_ignore(repo, git_ignore, project_path)

        if url and repo.get_remote_url != url:
            repo.add_remote(url)
            try:
                repo.set_upstream("main")
            except:
                pass

    def _clone(self, url, project_path, project, git_ignore, progress):
        try:
            repo = GitRepository.clone(url, project_path, self.context.username, self.context.email, progress=helper.CloneProgress(progress))
            progress.finish()
        
            helper.update_project(project_path, url, False, None, project, True)
            self._add_git_ignore(repo, git_ignore, project_path)
        except Exception as e:
            print(e)
            raise Exception("You might have entered a wrong username / password,<br>or you don't have access to the repository.")

    def _add_git_ignore(self, repo, ignore_value, project_path):
        repo.ignore(".ap/project.json", local_only=True)
        repo.ignore("*.approj", local_only=True)
        if ignore_value != "None":
            from add_ignore_config import add_git_ignore
            add_git_ignore(ignore_value, project_path, self.context.yaml_dir)
        
    def _folder_empty(self, folder_path):
        content = os.listdir(folder_path)
        if len(content) == 0: return True
        if platform.system() == "Darwin" and len(content) == 1:
            # macOS .DS_Store causes git clone to fail even if the rest of the folder is empty
            ds_store = os.path.join(folder_path, ".DS_Store")
            if platform.system() == "Darwin" and os.path.exists(ds_store):
                os.remove(ds_store)
                return True

        return False

    def _get_git_parent_dir(self, folder_path):
        for root, dirs, _ in os.walk(folder_path):
            for dir in dirs:
                if dir == ".git":
                    return os.path.join(root, dir)
        return None

    def _is_path_equal(self, path1: str, path2: str):
        if path1 == None or path2 == None: return False
        
        norm1 = os.path.normpath(os.path.normcase(path1))
        norm2 = os.path.normpath(os.path.normcase(path2))
        return norm1 == norm2

def on_show_create_project(project_types, path: str, ctx: ap.Context):
    import os
    iconPath = os.path.join(ctx.yaml_dir, "icons/project_type_git.svg")
    gitProjectType = GitProjectType(path, ctx)
    gitProjectType.name = 'Git Repository'
    gitProjectType.description = 'Open or create a Git repository for your <font color=#FFFFFF>Unreal</font> or <font color=#FFFFFF>Unity</font> project. Connect it to Git providers such as GitHub, Azure Devops or self-hosted Git servers.'
    gitProjectType.priority = 100
    gitProjectType.pre_selected = False
    if path:
        git_path = os.path.join(path, ".git")
        gitProjectType.pre_selected = os.path.exists(git_path)
    
    gitProjectType.icon = iconPath
    project_types.add(gitProjectType)