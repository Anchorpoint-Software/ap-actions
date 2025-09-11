import anchorpoint as ap
import apsync as aps
import platform
import os
import sys


def validate_path(dialog: ap.Dialog, value):
    if not value or len(value) == 0:
        return False, "Please add a folder for your project files"
    if not os.path.exists(value):
        return False, "Please add a real folder"
    else:
        return True, None


def get_workspace_template_dir():
    ctx = ap.get_context()
    settings = aps.SharedSettings(ctx.workspace_id, "inc_workspace_settings")
    template_dir_win = settings.get("template_dir_win")
    template_dir_mac = settings.get("template_dir_mac")

    if platform.system() == "Darwin":
        return template_dir_mac
    else:
        return template_dir_win


class IncProjectType(ap.ProjectType):
    def __init__(self, path: str, remote: str, tags, ctx: ap.Context):
        super().__init__()
        self.context = ctx
        self.path = path
        self.icon = os.path.join(os.path.dirname(__file__), "dcc_project.svg")
        self.pre_selected = True

        self.dialog = ap.Dialog("CreateIncProjectDialog")
        self.local_settings = aps.Settings("inc_local_settings")
        self.shared_settings = aps.SharedSettings(
            ctx.workspace_id, "inc_workspace_settings")
        self.tokens = self.shared_settings.get("tokens", [])
        template_empty = self.shared_settings.get(
            "template_dir_win") == "" and self.shared_settings.get("template_dir_mac") == ""

        self.dialog.add_input(
            var="project_path",
            browse_path=self.local_settings.get("prev_project_path", ""),
            placeholder="Z:\\Projects\\ACME_Corp_AB434",
            width=420,
            browse=ap.BrowseType.Folder,
            validate_callback=validate_path,
        )
        if not template_empty:
            self.dialog.add_checkbox(False,
                                     text="Use Folder Structure Template", var="use_template")
            self.dialog.add_info(
                "Populates a folder structure from a template. The selected project folder has to be empty<br>in this case.")
        if self.tokens != []:
            self.dialog.add_text("<b>Tokens</b>")
            for token in self.tokens:
                self.dialog.add_text(token, width=70).add_input(
                    var=f"{token}_token_var", width=200, placeholder="Enter something")
            self.dialog.add_info(
                "Tokens are used to manage additional project information and for naming conventions")

    def get_dialog(self):
        return self.dialog

    def get_project_name_candidate(self):
        return os.path.basename(self.dialog.get_value("project_path"))

    def get_project_path(self):
        return self.dialog.get_value("project_path")

    def project_created(self):
        pass

    def setup_project(self, project_id: str, progress):

        # store project parent path for next time
        project_path = self.dialog.get_value("project_path")
        parent_path = os.path.dirname(project_path.rstrip("\\/"))
        # If parent_path is empty or same as project_path, it's a root drive
        if parent_path and parent_path != project_path:
            self.local_settings.set("prev_project_path", parent_path)
        else:
            self.local_settings.set("prev_project_path", project_path)
        self.local_settings.store()

        # Make the project folder
        project_path = self.get_project_path()
        os.makedirs(project_path, exist_ok=True)

        # Access the project settings for storing the tokens
        project_settings = aps.SharedSettings(
            project_id, self.context.workspace_id, "inc_settings")

        # Copy from template and resolve token placeholders
        project_name = aps.get_project_by_id(
            project_id, self.context.workspace_id).name.replace(" ", "_")

        variables = {"project_name": project_name}
        # variable structure example: {"client_name": "some_client","country_code":"de"}
        for token in self.tokens:
            value = self.dialog.get_value(
                f"{token}_token_var").strip()
            if value != "":
                variables[token] = value

        # Store the tokens so that they can be used later
        project_settings.set("tokens", variables)
        project_settings.store()

        # Apply the template if the checkbox is checked
        if self.dialog.get_value("use_template"):
            template_dir = get_workspace_template_dir()
            if not template_dir or not os.path.exists(template_dir):
                ap.UI().show_error("Template directory is not set or does not exist.")
                sys.exit(0)

            progress.set_text("Creating from template...")

            try:
                aps.copy_from_template(template_dir, project_path, variables)
            except Exception as e:
                ap.UI().show_error("Error copying template", e)
                return

        self.project = aps.get_project_by_id(
            project_id, self.context.workspace_id)
        self.path = project_path

        channel = aps.TimelineChannel()
        channel.id = "inc-vc-basic"
        channel.name = "Published incremental saves"

        aps.add_timeline_channel(self.project, channel)


def on_show_create_project(project_types, integrations, path: str, remote: str, tags, ctx: ap.Context):
    inc_project_type = IncProjectType(path, remote, tags, ctx)
    inc_project_type.name = "Shared Folder with Publish Workflow"
    inc_project_type.description = "Store files on a <span style='color:white'>shared folder</span> with <span style='color:white'>incremental file versioning</span> and publish versions to the timeline via DCC plugins."
    inc_project_type.priority = 200
    inc_project_type.pre_selected = True
    project_types.add(inc_project_type)
