import anchorpoint as ap
import apsync as aps
import os
import subprocess
import platform


plugin_action_id = "open_plugin_directory"

# Hook, triggered by Anchorpoint


def on_load_integrations(integrations, ctx: ap.Context):
    integration = Cinema4DIntegration(ctx)
    integrations.add(integration)


class Cinema4DIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()

        self.ctx = ctx
        self.name = "Cinema 4D"
        self.description = "Publish incremental file versions from Cinema 4D and automate pipeline steps. Useful for product visualization and asset creation workflows."
        self.priority = 100
        self.dashboard_icon = os.path.join(ctx.yaml_dir, "cinema_4d.svg")
        self.preferences_icon = os.path.join(ctx.yaml_dir, "cinema_4d.svg")

        # settings = aps.Settings("cinema4D")

        # self.is_connected = True  # is_connected()

        plugin_folder = ap.IntegrationAction()
        plugin_folder.name = "Open Plugin"
        plugin_folder.enabled = True
        plugin_folder.icon = aps.Icon(os.path.join(
            os.path.dirname(ctx.yaml_dir), "folder_grey.svg"))
        plugin_folder.identifier = plugin_action_id
        plugin_folder.tooltip = "Copy and paste the plugin to your Cinema 4D plugin directory"
        self.add_preferences_action(plugin_folder)

    def execute_preferences_action(self, action_id: str):
        if action_id == plugin_action_id:
            system = platform.system()
            path = os.path.join(self.ctx.yaml_dir, "plugin")

            if system == "Windows":
                # Open folder or select a file
                if os.path.isfile(path):
                    subprocess.run(
                        ["explorer", "/select,", os.path.normpath(path)])
                else:
                    subprocess.run(["explorer", os.path.normpath(path)])
            elif system == "Darwin":  # macOS
                if os.path.isfile(path):
                    subprocess.run(["open", "-R", path])
                else:
                    subprocess.run(["open", path])
            else:  # Linux, fallback
                subprocess.run(["xdg-open", path])
