import anchorpoint as ap
import apsync as aps

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        from is_git_repo import is_git_repo
        if is_git_repo(path): return False
        return True
    except Exception as e:
        return False

if __name__ == "__main__":
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..")
    sys.path.insert(0, script_dir)

    try:
        from vc.apgit.repository import * 
    except Warning as e:
        sys.exit(0)

    import git_repository_helper as helper
    sys.path.remove(script_dir)

    ctx = ap.Context.instance()
    ui = ap.UI()
    location = ctx.path
    yaml_dir = ctx.yaml_dir

    workspace_id = ctx.workspace_id         

    def navigate():
        import time
        time.sleep(0.5)
        ui.navigate_to_folder(location)
        ui.show_success("Git Repository Initialized")

    def create_repo(dialog: ap.Dialog):
        repo_path = location
        remote = dialog.get_value("remote")
        url = dialog.get_value("url")
        name = dialog.get_value("name")
        ignore = dialog.get_value("dropdown")
        
        if GitRepository.is_repo(repo_path):
            ap.UI().show_info("Already a Git repo")
            return False
        else:
            remote_exists = remote and len(url) > 0
            project = ctx.create_project(location, name, workspace_id)
            repo = GitRepository.create(repo_path, ctx.username, ctx.email)
            if remote_exists:
                helper.update_project(repo_path, url, False, None, project, add_path=False)
            else:
                helper.update_project(repo_path, None, False, None, project, add_path=False)
            repo.ignore(".ap/project.json", local_only=True)
            if remote_exists > 0:
                repo.add_remote(url)

            if ignore != "None":
                from add_ignore_config import add_git_ignore
                add_git_ignore(ignore, location, yaml_dir)

            ctx.run_async(navigate)

            dialog.close()
            return True

    def update_dialog(dialog: ap.Dialog, value):
        name = dialog.get_value("name")
        url = dialog.get_value("url")
        remote_enabled = dialog.get_value("remote")
        hide_remote_settings = not remote_enabled

        dialog.hide_row("repotext", hide_remote_settings)
        dialog.hide_row("url", hide_remote_settings)

        enable = len(name) > 0
        if remote_enabled:
            enable = enable and len(url) > 0

        dialog.set_enabled("create", enable)

    from add_ignore_config import get_ignore_file_types
    dropdown_values = get_ignore_file_types(ctx.yaml_dir)
    dropdown_values.insert(0, "None")

    project_name = os.path.basename(ctx.path)

    dialog = ap.Dialog()
    dialog.title = "Import as Git repository"
    dialog.icon = ctx.icon

    dialog.add_text("Project Name:     ").add_input(var="name", default=project_name)
    dialog.add_text("GitIgnore Config:").add_dropdown(dropdown_values[0], dropdown_values, var="dropdown")
    dialog.add_info("Add a <b>gitignore</b> to your project to exclude certain files from being<br> committed to Git (e.g. Unreal Engine's build result).")

    dialog.add_switch(True, var="remote", callback=update_dialog).add_text("Remote Repository")
    dialog.add_info("Create a local Git repository or connect it to a remote like GitHub")

    dialog.add_text("<b>Repository URL</b>", var="repotext")
    dialog.add_input(placeholder="https://github.com/Anchorpoint-Software/ap-actions.git", var="url", width = 400, callback=update_dialog)

    dialog.add_empty()
    dialog.add_button("Create", var="create", callback=create_repo, enabled=False)
    dialog.show()