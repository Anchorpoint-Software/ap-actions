import anchorpoint as ap
import apsync as aps

if __name__ == "__main__":
    import sys, os, importlib
    sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

    importlib.invalidate_caches()

    try:
        from vc.apgit.repository import * 
    except Warning as e:
        sys.exit(0)

    import platform
    import git_repository_helper as helper

    ctx = ap.Context.instance()
    ui = ap.UI()

    project_id = ctx.project_id
    workspace_id = ctx.workspace_id
    project = aps.get_project_by_id(project_id, workspace_id)
    if not project:
        ui.show_error("Cannot connect git repository", "You must create a project first")
        sys.exit(0) 

    timeline_channel = aps.get_timeline_channel(project, helper.CHANNEL_ID)
    settings = aps.Settings()

    def connect_repo(dialog: ap.Dialog):
        location = dialog.get_value("location")
        repo_path = location
        if not GitRepository.is_repo(repo_path):
            ui.show_info("Could not connect Git Repository", "Folder does not contain a Git repo")
        else:
            repo = GitRepository.load(repo_path)
            if not repo:
                ui.show_error("Invalid Repo", "The git repository cannot be opened")
                return

            try:
                helper.update_project(repo_path, None, False, project_id, workspace_id, timeline_channel, project)
            except:
                ui.show_error("Could not connect Git Repository", "Folder does already contain an Anchorpoint project")
                return
            repo.ignore(".ap/project.json", local_only=True)
            ui.show_success("Git Repository Connected")
            dialog.close()

    def update_dialog(dialog: ap.Dialog, value):
        location = dialog.get_value("location")
        dialog.set_enabled("connect", len(location) > 0)

        settings.set("browse_path", location)
        settings.store()

    remote_enabled = True
    remote_toggleable = not timeline_channel or "gitRemoteUrl" not in timeline_channel.metadata
    if not remote_toggleable:
        remote_url = timeline_channel.metadata["gitRemoteUrl"]
    else:
        remote_url = ""

    hide_remote_settings = not remote_enabled

    dialog = ap.Dialog()
    dialog.title = "Connect Git repository"
    dialog.icon = ctx.icon

    dialog.add_text("<b>Git Project Folder</b>")
    if platform.system() == "Windows":
        dialog.add_input(placeholder="D:/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)
    else:
        dialog.add_input(placeholder="/users/johndoe/Projects/projectname", var="location", width = 400, browse=ap.BrowseType.Folder, callback=update_dialog)

    browse_path = settings.get("browse_path")
    if browse_path is not None:
        dialog.set_browse_path(var="location", path=browse_path)

    dialog.add_empty()
    dialog.add_button("Connect", var="connect", callback=connect_repo, enabled=False)
    dialog.show()