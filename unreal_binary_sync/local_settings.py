import anchorpoint as ap
import apsync as aps
import os


class UnrealProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        if ctx.project_id is None or ctx.project_id == "":
            raise Exception(
                "Unreal Binary settings can only be used in the context of a project"
            )

        no_project_label = "No Project"

        # Check if it's an Unreal project based on located .uproject files
        uproject_files = self.find_uproject_files(ctx.project_path)
        uproject_display_names = [os.path.splitext(os.path.basename(uproject_file))[
            0] for uproject_file in uproject_files]
        uproject_display_names.append(no_project_label)

        self.ctx = ctx
        project_path = ctx.project_path

        # Get local and shared settings
        local_settings = aps.Settings()
        binary_source = local_settings.get(project_path+"_binary_source", "")
        sync_dependencies = local_settings.get(
            project_path+"_sync_dependencies", False)
        launch_project_display_name = local_settings.get(
            project_path+"_launch_project_display_name", no_project_label)
        enable_binary_pull = local_settings.get(
            project_path+"_enable_binary_auto_pull", False)
        enable_binary_push = local_settings.get(
            project_path+"_enable_binary_push", False)
        engine_directory = local_settings.get(
            project_path+"_engine_directory", "")

        self.shared_settings = aps.SharedSettings(
            ctx.workspace_id, "unreal_binary_sync")

        self.binary_location = self.shared_settings.get(
            "binary_location_type", "folder")

        self.dialog = ap.Dialog()

        if self.binary_location == "folder":
            self.dialog.add_text("ZIP Location", width=100).add_input(
                placeholder="Select folder containing binaries...",
                browse=ap.BrowseType.Folder,
                var="binary_source",
                default=binary_source,
                width=246,
                callback=self.store_local_settings
            )
            self.dialog.add_info(
                "The folder containing all the ZIP files named with commit IDs. Learn how to<br>properly <a href='https://docs.anchorpoint.app/docs/version-control/features/binary-sync/' >setup binary syncing</a>.")

        self.dialog.add_checkbox(
            text="Sync Setup Dependencies",
            var="sync_dependencies",
            default=sync_dependencies,
            callback=self.store_local_settings
        )
        self.dialog.add_info(
            "Only applicable when you build the <a href='https://docs.anchorpoint.app/docs/version-control/features/binary-sync/#case-2-building-the-unreal-editor-from-source'>engine from source</a>. Note that you have to<br>accept a Windows Control Popup for UE Prerequisites.")

        self.dialog.add_text("Launch Project", width=110).add_dropdown(
            default=launch_project_display_name,
            values=uproject_display_names,
            var="launch_project_display_name",
            callback=self.store_local_settings
        )
        self.dialog.add_info(
            "Launch the Unreal Editor when the sync is complete")

        self.dialog.add_checkbox(text="Enable Binary Sync on Pull", var="enable_binary_pull",
                                 default=enable_binary_pull, callback=self.store_local_settings)
        self.dialog.add_info(
            "Sync the project binaries when pulling changes from the repository.")
        self.dialog.add_empty()
        self.dialog.add_text("<b>Binary Submission Settings</b>")
        self.dialog.add_checkbox(text="Add Binary Push Button", var="enable_binary_push",
                                 default=enable_binary_push, callback=self.enable_binary_push)
        self.dialog.add_text("Engine Directory", width=110).add_input(
            placeholder=r"C:\Program Files\Epic Games\UE_5.6",
            browse=ap.BrowseType.Folder,
            width=266,
            default=engine_directory,
            var="engine_directory",
            callback=self.store_local_settings)
        self.dialog.add_info(
            "Only applicable when you use the Unreal Engine version from the Epic Games<br>Launcher. Add a sidebar button to compile and push the project binaries when<br>pushing changes to the repository. Learn more about <a href='https://docs.anchorpoint.app/docs/version-control/features/binary-sync/#setup-the-binary-sync-action-in-anchorpoint'>pushing binaries</a>.")

    def get_dialog(self):
        return self.dialog

    def find_uproject_files(self, project_path):

        uproject_files = []
        depth = 3  # only dive in 3 subfolder levels

        # Get all directories at the specified depth (currently set to depth levels)
        for root, dirs, files in os.walk(project_path, topdown=True):
            # Skip Engine and Templates folders
            if 'Engine' in dirs:
                dirs.remove('Engine')
            if 'Templates' in dirs:
                dirs.remove('Templates')

            # Only process up to depth levels deep
            rel_path = os.path.relpath(root, project_path)
            if rel_path == '.' or rel_path.count(os.sep) <= depth:
                # Look for .uproject files in current directory
                for file in files:
                    if file.endswith('.uproject'):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, project_path)
                        uproject_files.append(rel_path)

            # Stop walking deeper than depth levels
            if rel_path.count(os.sep) >= depth:
                dirs.clear()

        return uproject_files

    def enable_binary_push(self, dialog, value):
        dialog.set_enabled("engine_directory", value)
        ap.UI().show_info("Project refresh needed",
                          "Close and reopen the project to change the sidebar button state")
        self.store_local_settings(dialog, value)
        return

    def store_local_settings(self, dialog, value):

        ctx = ap.get_context()
        project_path = ctx.project_path

        # Store the settings for next time
        local_settings = aps.Settings()
        if self.binary_location == "folder":
            local_settings.set(project_path+"_binary_source",
                               dialog.get_value("binary_source"))
        local_settings.set(project_path+"_sync_dependencies",
                           dialog.get_value("sync_dependencies"))
        local_settings.set(project_path+"_launch_project_display_name",
                           dialog.get_value("launch_project_display_name"))

        local_settings.set(
            project_path+"_enable_binary_auto_pull", dialog.get_value("enable_binary_pull"))
        local_settings.set(project_path+"_engine_directory",
                           dialog.get_value("engine_directory"))
        local_settings.set(
            project_path+"_enable_binary_push", dialog.get_value("enable_binary_push"))

        local_settings.store()
        return


def on_show_project_preferences(settings_list, ctx: ap.Context):
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project:
        return

    unrealSettings = UnrealProjectSettings(ctx)
    unrealSettings.name = "Unreal"
    unrealSettings.priority = 90
    unrealSettings.icon = ":/icons/organizations-and-products/unrealEngine.svg"
    settings_list.add(unrealSettings)
