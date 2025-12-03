import maya.cmds as cmds  # pyright: ignore[reportMissingImports]
import maya.api.OpenMaya as om  # pyright: ignore[reportMissingImports]
import maya.utils  # pyright: ignore[reportMissingImports]
import subprocess
import os
import json
import platform
import threading
import glob
import tempfile


def maya_useNewAPI():
    pass

# Check if the file is in an Anchorpoint project


# Check if the file is in an Anchorpoint project
def is_in_anchorpoint_project(file_path: str) -> bool:
    if not file_path:
        return False

    # Start at the folder containing the file (or the folder itself if it's a directory)
    if os.path.isfile(file_path):
        current_dir = os.path.dirname(os.path.abspath(file_path))
    else:
        current_dir = os.path.abspath(file_path)

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


def get_executable_path():
    if platform.system() == "Windows":
        cli_path = os.path.join(
            os.getenv("APPDATA"), "Anchorpoint Software", "Anchorpoint", "app", "ap.exe"
        )  # pyright: ignore[reportCallIssue]

    elif platform.system() == "Darwin":  # macOS
        cli_path = "/Applications/Anchorpoint.app/Contents/Frameworks/ap"        

    if os.path.exists(cli_path):
        return cli_path
    else:
        raise FileNotFoundError("CLI Not Installed!")


def capture_viewport_screenshot():
    try:
        # Use the system temp directory
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "ap_maya_screenshot.png")

        # Get the active model panel (viewport)
        panel = cmds.getPanel(withFocus=True)
        if not panel or not cmds.getPanel(typeOf=panel) == "modelPanel":
            # Fallback: first available modelPanel
            model_panels = cmds.getPanel(type="modelPanel")
            panel = model_panels[0] if model_panels else None

        if not panel:
            raise RuntimeError("No active model panel found for screenshot")

        # Capture viewport as an image (png)
        cmds.playblast(
            completeFilename=output_path,
            forceOverwrite=True,
            format="image",
            compression="png",
            width=960,
            height=540,
            quality=100,
            showOrnaments=False,
            viewer=False,
            frame=cmds.currentTime(q=True),
            offScreen=True,
            percent=100,
            clearCache=True
        )

        return output_path
    except Exception as e:
        print(f"Failed to capture viewport screenshot: {e}")
        return None


def run_executable(msg, path):
    def execute_command():
        try:
            maya.utils.executeInMainThreadWithResult(
                lambda: cmds.headsUpMessage("Talking to Anchorpoint")
            )

            executable_path = get_executable_path()
            screenshot_path = maya.utils.executeInMainThreadWithResult(
                lambda: capture_viewport_screenshot()
            )
            json_object = {
                "msg": str(msg),
                "doc-path": str(path),
                "screenshot": str(screenshot_path)
            }
            payload = json.dumps(json_object, ensure_ascii=False)

            plugin_path = cmds.pluginInfo(
                "anchorpoint_plugin", q=True, path=True)
            plugin_dir = os.path.dirname(plugin_path)

            script_path = os.path.join(
                os.path.dirname(os.path.dirname(plugin_dir)),
                "cmd_to_ap.py"
            )
            if not os.path.exists(script_path):
                script_path = os.path.join(
                    os.path.dirname(executable_path),
                    "scripts", "ap-actions", "dcc_pipeline_tools", "cmd_to_ap.py"
                )

            command = [
                executable_path,
                '--cwd', os.path.dirname(path),
                'python',
                '-s',
                script_path,
                '--args',
                payload,
            ]

            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                startupinfo=startupinfo
            )

            if result.stderr:
                print(result.stderr)
                maya.utils.executeInMainThreadWithResult(
                    lambda: cmds.confirmDialog(
                        title="Error", message="An issue has occurred")
                )
            else:
                maya.utils.executeInMainThreadWithResult(
                    lambda: cmds.confirmDialog(
                        title="Success", message=result.stdout)
                )

        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")
        finally:
            maya.utils.executeInMainThreadWithResult(
                lambda: cmds.headsUpMessage("")
            )

    threading.Thread(target=execute_command).start()


def _env_for_clean_qt():
    env = os.environ.copy()
    # Apply neutral High-DPI settings for the child Qt app
    env["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    return env


def open_anchorpoint_with_file():
    current_file = cmds.file(query=True, sceneName=True)
    if not current_file:
        cmds.confirmDialog(
            title="Error",
            message="Document must be saved before opening Anchorpoint."
        )
        return

    try:
        env = _env_for_clean_qt()

        if platform.system() == "Windows":
            appdata = os.getenv('LOCALAPPDATA')
            anchorpoint_exe = os.path.join(appdata, "Anchorpoint", "anchorpoint.exe")  # pyright: ignore[reportCallIssue]
            if not os.path.exists(anchorpoint_exe):
                cmds.confirmDialog(
                    title="Error", message="Anchorpoint executable not found!")
                return

            # Detach + no console to keep things clean and fully separate from Maya
            creationflags = 0
            try:
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            except AttributeError:
                # On some Python builds these flags may not exist; it's fine to skip.
                creationflags = 0

            subprocess.Popen(
                [anchorpoint_exe, current_file],
                shell=False,
                env=env,
                creationflags=creationflags,
                startupinfo=None  # or a hidden STARTUPINFO if you prefer
            )

        elif platform.system() == "Darwin":
            anchorpoint_app = "/Applications/Anchorpoint.app/Contents/MacOS/Anchorpoint"
            if not os.path.exists(anchorpoint_app):
                cmds.confirmDialog(
                    title="Error", message="Anchorpoint app not found!")
                return

            # Use the sanitized env (replaces your previous hard-coded QT_SCALE_FACTOR=1)
            subprocess.Popen([anchorpoint_app, current_file], env=env)

        else:
            cmds.confirmDialog(title="Error", message="Unsupported OS")

    except Exception as e:
        cmds.confirmDialog(
            title="Error", message=f"Failed to open Anchorpoint: {e}")


def show_publish_dialog():
    current_file = cmds.file(query=True, sceneName=True)
    if not current_file:
        cmds.confirmDialog(
            title="Error", message="Document must be saved before publishing.")
        return
    if not is_in_anchorpoint_project(current_file):
        cmds.confirmDialog(
            title="Error",
            message="This file is not inside an Anchorpoint project."
        )
        return

    result = cmds.promptDialog(
        title="Publish Current Version",
        message="Enter a comment for this version:",
        button=["Publish", "Cancel"],
        defaultButton="Publish",
        cancelButton="Cancel",
        dismissString="Cancel"
    )
    if result == "Publish":
        user_message = cmds.promptDialog(query=True, text=True)
        if not user_message.strip():
            cmds.confirmDialog(title="Error", message="Please enter a comment")
            return
        run_executable(user_message, current_file)


def create_anchorpoint_menu():
    menu_name = "Anchorpoint"
    if cmds.menu(menu_name, exists=True):
        cmds.deleteUI(menu_name)
    cmds.menu(menu_name, label=menu_name, parent="MayaWindow")
    cmds.menuItem(
        label="Open in Anchorpoint",
        command=lambda *args: open_anchorpoint_with_file()
    )
    cmds.menuItem(
        label="Publish",
        command=lambda *args: show_publish_dialog()
    )


def initializePlugin(mobject):
    plugin = om.MFnPlugin(
        mobject,
        "Anchorpoint Software GmbH",  # vendor
        "1.0.0",                      # version string
        "Any"                         # API version
    )
    create_anchorpoint_menu()


def uninitializePlugin(mobject):
    plugin = om.MFnPlugin(mobject)
    menu_name = "Anchorpoint"
    if cmds.menu(menu_name, exists=True):
        cmds.deleteUI(menu_name)
