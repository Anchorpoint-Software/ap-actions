import c4d
from c4d import gui, plugins
import subprocess
import os
import json
import re
import platform
import threading
import glob

PLUGIN_ID_0 = 1066244  # Is registered on plugin cafe
PLUGIN_ID_1 = 1064547  # Is registered on plugin cafe

# Summary
# This plugin creates a menu entry called "Anchorpoint/ Publish" in the Cinema 4D main menu.
# It opens a dialog where the user can enter a comment and publish the current version of the Cinema 4D file to Anchorpoint.
# It retrieves the path of the currently open document, constructs a command to the Anchorpoint CLI with an external Python script (which is in the same folder), that connects to the Anchorpoint metadata database,
# and passes the user input as a JSON string.


# Check if the file is in an Anchorpoint project
def is_in_anchorpoint_project(file_path: str) -> bool:
    if not file_path:
        return False

    # Start at the folder containing the file
    current_dir = os.path.dirname(os.path.abspath(file_path))

    while True:
        # Look for any .approj file in this folder
        if glob.glob(os.path.join(current_dir, "*.approj")):
            return True

        # Move one level up
        parent_dir = os.path.dirname(current_dir)

        # Stop if we've reached the root (no higher dir exists)
        if parent_dir == current_dir:
            break

        current_dir = parent_dir

    return False


# Make run_executable available to all classes


def run_executable(msg, path):
    def execute_command():
        try:
            c4d_version = c4d.GetC4DVersion() // 1000
            # Show busy indicator depending on c4d version
            if c4d_version <= 2024:
                c4d.StatusSetText("Talking to Anchorpoint")
                c4d.StatusSetSpin()
            else:
                gui.StatusSetText("Talking to Anchorpoint")
                gui.StatusSetSpin()

            executable_path = get_executable_path()
            # Ensure all values are serializable (strings)
            json_object = {
                "msg": str(msg),
                "path": str(path)
            }
            json_string = json.dumps(json_object)
            # Try to get the script path if the plugin is relative to the Anchorpoint installation folder
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                __file__)))), "cmd_to_ap.py")

            # Use the file path relative to the ap.exe if the other one does not exist
            if not os.path.exists(script_path):
                script_path = os.path.join(os.path.dirname(
                    executable_path), "scripts", "ap-actions", "dcc_pipeline_tools", "cmd_to_ap.py")

            # Prepare the command
            command = [
                executable_path,
                '--cwd', os.path.dirname(path),
                'python',
                '-s',
                script_path,
                '--args',
                json_string,
            ]
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            if result.stderr:
                print(result.stderr)
                gui.MessageDialog("An issue has occurred")
            else:
                gui.MessageDialog(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        finally:
            if c4d_version <= 2024:
                c4d.StatusClear()
            else:
                gui.StatusClear()
    threading.Thread(target=execute_command).start()


def open_anchorpoint_with_file():
    doc = c4d.documents.GetActiveDocument()
    doc_path = doc.GetDocumentPath()
    doc_name = doc.GetDocumentName()
    if not doc_path or not doc_name:
        gui.MessageDialog("Document must be saved before opening Anchorpoint.")
        return
    file_path = os.path.join(doc_path, doc_name)
    try:
        if platform.system() == "Windows":
            # Use the user's home directory for AppData
            appdata = os.getenv('LOCALAPPDATA')
            anchorpoint_exe = os.path.join(
                appdata, "Anchorpoint", "anchorpoint.exe")
            if not os.path.exists(anchorpoint_exe):
                gui.MessageDialog("Anchorpoint executable not found!")
                return
            subprocess.Popen([anchorpoint_exe, file_path], shell=False)
        elif platform.system() == "Darwin":
            # On Mac, use the same directory as the CLI (see get_executable_path)
            anchorpoint_app = "/Applications/Anchorpoint.app/Contents/MacOS/Anchorpoint"
            if not os.path.exists(anchorpoint_app):
                gui.MessageDialog("Anchorpoint app not found!")
                return
            subprocess.Popen([anchorpoint_app, file_path])
        else:
            gui.MessageDialog("Unsupported OS")
    except Exception as e:
        gui.MessageDialog(f"Failed to open Anchorpoint: {e}")


def EnhanceMainMenu():
    mainMenu = gui.GetMenuResource("M_EDITOR")  # Get main menu resource

    # Create the Anchorpoint menu
    anchorpoint_menu = c4d.BaseContainer()
    anchorpoint_menu.InsData(c4d.MENURESOURCE_SUBTITLE, "Anchorpoint")
    # Insert 'Open Anchorpoint' first
    anchorpoint_menu.InsData(c4d.MENURESOURCE_COMMAND,
                             "PLUGIN_CMD_{}".format(PLUGIN_ID_0))
    # Then the existing Publish command
    anchorpoint_menu.InsData(c4d.MENURESOURCE_COMMAND,
                             "PLUGIN_CMD_{}".format(PLUGIN_ID_1))

    # Add the Anchorpoint menu to the main menu
    if mainMenu:
        mainMenu.InsData(c4d.MENURESOURCE_STRING, anchorpoint_menu)


def PluginMessage(id, data):
    if id == c4d.C4DPL_BUILDMENU:
        EnhanceMainMenu()


def get_executable_path():
    if platform.system() == "Windows":
        base_path = os.path.join(os.getenv('LOCALAPPDATA'), "Anchorpoint")
        pattern = r"app-(\d+\.\d+\.\d+)"
        cli_executable_name = "ap.exe"

        # Get directories matching the pattern
        versioned_directories = [
            d for d in os.listdir(base_path)
            if re.match(pattern, d)
        ]

        # Sort directories by version
        versioned_directories.sort(key=lambda d: tuple(
            map(int, re.match(pattern, d).group(1).split('.'))), reverse=True)

        if versioned_directories:
            latest_version_path = os.path.join(
                base_path, versioned_directories[0])
            cli_path = os.path.join(latest_version_path, cli_executable_name)

            if os.path.exists(cli_path):
                return cli_path
            else:
                raise FileNotFoundError("CLI Not Installed!")

    elif platform.system() == "Darwin":  # macOS
        cli_path = "/Applications/Anchorpoint.app/Contents/Frameworks/ap"

        if os.path.exists(cli_path):
            return cli_path
        else:
            raise FileNotFoundError("CLI Not Installed!")

    else:
        raise OSError("Unsupported OS")


class PublishLatestVersion(gui.GeDialog):
    def CreateLayout(self):
        self.SetTitle("Publish Current Version")

        # Add infotext above the text field
        self.AddStaticText(
            1004, 460, 0, name="Publishing will create a new version in Anchorpoint")

        self.AddMultiLineEditText(1003, c4d.BFH_SCALEFIT, 256, 40)
        self.AddButton(1001, c4d.BFH_SCALEFIT, 256, 0, name="Publish")

        return True

    def OpenDialog(self, dlgtype):
        # Open the dialog in the center of the application
        self.Open(dlgtype, -1, -1)

    def Command(self, id, msg):
        if id == 1001:  # Open button clicked
            user_message = self.GetString(1003)
            if not user_message.strip():
                gui.MessageDialog("Please enter a comment")
                return True
            doc = c4d.documents.GetActiveDocument()
            doc_path = doc.GetDocumentPath()
            doc_name = doc.GetDocumentName()
            if not doc_path or not doc_name:
                gui.MessageDialog("Document must be saved before publishing.")
                return True
            file_path = os.path.join(doc_path, doc_name)
            run_executable(str(user_message), file_path)
            self.Close()
        return True


class PublishLatestVersionCommand(plugins.CommandData):
    def Execute(self, doc):
        doc = c4d.documents.GetActiveDocument()
        doc_path = doc.GetDocumentPath()
        if doc is None or not doc.GetDocumentPath():
            gui.MessageDialog("You have to save your file first")
            return False

        if not is_in_anchorpoint_project(doc_path):
            gui.MessageDialog(
                "This file is not part of an Anchorpoint project")
            return False

        dialog = PublishLatestVersion()
        dialog.OpenDialog(c4d.DLG_TYPE_MODAL)
        return True

    def GetResourceString(self):
        return {
            "en": {
                "name": "Publish",
                "description": "Sets your current file as latest version"
            },
            "de": {
                "name": "Veröffentlichen",
                "description": "Kennzeichnet diese Datei als letzte Version"
            }
        }


class OpenAnchorpointCommand(plugins.CommandData):
    def Execute(self, doc):
        open_anchorpoint_with_file()
        return True

    def GetResourceString(self):
        return {
            "en": {
                "name": "Open Anchorpoint",
                "description": "Opens Anchorpoint application"
            },
            "de": {
                "name": "Anchorpoint öffnen",
                "description": "Öffnet die Anchorpoint Anwendung"
            }
        }


if __name__ == "__main__":
    # Load the icon from the file
    pub_icon = c4d.bitmaps.BaseBitmap()
    pub_icon_path = os.path.join(os.path.dirname(__file__), "publish.png")
    if pub_icon.InitWith(pub_icon_path)[0] != c4d.IMAGERESULT_OK:
        pub_icon = None  # Fallback if the icon fails to load

    ap_icon = c4d.bitmaps.BaseBitmap()
    ap_icon_path = os.path.join(os.path.dirname(__file__), "open.png")
    if ap_icon.InitWith(ap_icon_path)[0] != c4d.IMAGERESULT_OK:
        ap_icon = None  # Fallback if the icon fails to load

    # Register the command plugin for Open Anchorpoint
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID_0,
        str="Open Anchorpoint",
        info=c4d.PLUGINFLAG_HIDE,
        icon=ap_icon,
        help="Opens Anchorpoint application",
        dat=OpenAnchorpointCommand()
    )

    # Register the command plugin for Publish
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID_1,
        str="Publish",
        info=c4d.PLUGINFLAG_HIDE,
        icon=pub_icon,
        help="Sets this file as a latest version and allows to add a comment",
        dat=PublishLatestVersionCommand()
    )
