import anchorpoint as ap
import apsync as aps

# Register the Project Settings type, so that it can be accessed from the Project Settings in Anchorpoint


class IncProjectSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        if ctx.project_id is None or ctx.project_id == "":
            raise Exception(
                "Inc project settings can only be used inside a project"
            )

        self.project_id = ctx.project_id
        self.workspace_id = ctx.workspace_id

        self.shared_settings = aps.SharedSettings(
            self.project_id, self.workspace_id, "inc_settings")

        self.dialog = ap.Dialog()

        # Display local settings for all users
        self.dialog.add_text("<b>Publishing Settings</b>")

        self.dialog.add_checkbox(
            text="Create Master File per default",
            var="create_master_file",
            default=self.shared_settings.get("create_master_file", True),
            callback=self.store_shared_settings
        )
        self.dialog.add_text("File Appendix").add_input(
            placeholder="MyDocument_master.c4d",
            var="master_file_appendix",
            default=self.shared_settings.get("master_file_appendix", "master"),
            width=344,
            callback=self.store_shared_settings,
            enabled=self.dialog.get_value("create_master_file")
        )
        self.dialog.add_info(
            "Creates a copy of the latest incremental file version that can be referenced in other files")

        # Show tokens if they have been created during project creation
        tokens = self.shared_settings.get("tokens")
        if tokens:
            self.dialog.add_text("<b>Project Tokens</b>")
            for name, value in tokens.items():
                self.dialog.add_text(
                    name, width=100).add_text(value)
            self.dialog.add_info(
                "Tokens can replace [placeholders] in file names when creating from templates")

    def get_dialog(self):
        return self.dialog

    # Store settings on interface value changes
    def store_shared_settings(self, dialog, value):

        create_master_file = dialog.get_value("create_master_file")

        self.dialog.set_enabled("master_file_appendix", create_master_file)

        self.shared_settings.set("create_master_file", create_master_file)
        self.shared_settings.set("master_file_appendix",
                                 dialog.get_value("master_file_appendix"))
        self.shared_settings.store()
        return


def on_show_project_preferences(settings_list, ctx: ap.Context):
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if not project:
        return
    # Do not show the settings if it's not a inc versioning project, defined in inc_project.py
    channel = aps.get_timeline_channel(project, "inc-vc-basic")
    if not channel:
        return

    inc_project_settings = IncProjectSettings(ctx)
    inc_project_settings.name = "Workflow"
    inc_project_settings.priority = 90
    inc_project_settings.icon = ":/icons/Misc/single Version.svg"
    settings_list.add(inc_project_settings)
