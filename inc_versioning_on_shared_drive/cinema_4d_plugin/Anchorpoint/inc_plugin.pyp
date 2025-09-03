import c4d
from c4d import gui, plugins
import subprocess
import os
import json
import re
import platform
import threading

PLUGIN_ID = 1064547  # Is registered on plugin cafe

# Summary
# This plugin creates a menu entry called "Anchorpoint/ Publish" in the Cinema 4D main menu.
# It opens a dialog where the user can enter a comment and publish the current version of the Cinema 4D file to Anchorpoint.
# It retrieves the path of the currently open document, constructs a command to the Anchorpoint CLI with an external Python script (which is in the same folder), that connects to the Anchorpoint metadata database,
# and passes the user input as a JSON string.


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
            script_path = os.path.join(os.path.dirname(
                __file__), "inc_create_object.py")
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


def EnhanceMainMenu():
    mainMenu = gui.GetMenuResource("M_EDITOR")  # Get main menu resource

    # Create the Anchorpoint menu
    anchorpoint_menu = c4d.BaseContainer()
    anchorpoint_menu.InsData(c4d.MENURESOURCE_SUBTITLE, "Anchorpoint")
    anchorpoint_menu.InsData(c4d.MENURESOURCE_COMMAND,
                             "PLUGIN_CMD_" + str(PLUGIN_ID))
    anchorpoint_menu.InsData(c4d.MENURESOURCE_COMMAND,
                             "PLUGIN_CMD_" + str(PLUGIN_ID + 1))

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


if __name__ == "__main__":
    # Load the icon from the file
    pub_icon = c4d.bitmaps.BaseBitmap()
    pub_icon_path = os.path.join(os.path.dirname(__file__), "publish.png")
    if pub_icon.InitWith(pub_icon_path)[0] != c4d.IMAGERESULT_OK:
        pub_icon = None  # Fallback if the icon fails to load
    spl_icon = c4d.bitmaps.BaseBitmap()
    spl_icon_path = os.path.join(os.path.dirname(__file__), "splinter.png")
    if spl_icon.InitWith(spl_icon_path)[0] != c4d.IMAGERESULT_OK:
        spl_icon = None  # Fallback if the icon fails to load

    # Register the command plugin for Publish
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="Publish",
        info=c4d.PLUGINFLAG_HIDE,
        icon=pub_icon,
        help="Sets this file as a latest version and allows to add a comment",
        dat=PublishLatestVersionCommand()
    )
