bl_info = {
    "name": "Anchorpoint Integration",
    "author": "Anchorpoint",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Header > Anchorpoint Menu",
    "description": "Anchorpoint integration for Blender - Publish versions and open Anchorpoint",
    "category": "System",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty
import subprocess
import os
import json
import re
import platform
import threading
import glob

# Global variables for UI message display
_pending_message = None
_pending_title = "Anchorpoint"
_message_type = 'INFO'

def show_message_delayed(message, title="Anchorpoint", icon='INFO'):
    #Store message to be shown by timer callback
    global _pending_message, _message_type, _pending_title
    _pending_message = message
    _pending_title = title
    _message_type = icon
    # Register timer to show message in main thread
    bpy.app.timers.register(show_pending_message, first_interval=0.1)

def show_pending_message():
    #Timer callback to show pending message
    global _pending_message, _message_type, _pending_title
    if _pending_message:
        # Use the dialog operator with OK button
        bpy.ops.anchorpoint.show_message('INVOKE_DEFAULT', 
                                        message=_pending_message, 
                                        dialog_title=_pending_title)
        _pending_message = None
    return None  # Don't repeat timer



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
        cli_path = os.path.join(os.getenv('APPDATA'), "Anchorpoint Software", "Anchorpoint","app","ap.exe")

    elif platform.system() == "Darwin":  # macOS
        cli_path = "/Applications/Anchorpoint.app/Contents/Frameworks/ap"        

    if os.path.exists(cli_path):
        return cli_path
    else:
        raise FileNotFoundError("CLI Not Installed!")


def run_executable(msg, path):
    def execute_command():
        try:
            executable_path = get_executable_path()
            # Ensure all values are serializable (strings)
            json_object = {
                "msg": str(msg),
                "doc-path": str(path)
            }
            payload = json.dumps(json_object, ensure_ascii=False)
            # Try to get the script path if the plugin is relative to the Anchorpoint installation folder
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                __file__))), "cmd_to_ap.py")

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
                payload,
            ]
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            if result.stderr:
                print(f"Anchorpoint Error: {result.stderr}")
                show_message_delayed("An issue has occurred", "Anchorpoint Error", 'ERROR')
            else:
                output_msg = result.stdout.strip()
                print(f"Anchorpoint Success: {output_msg}")
                show_message_delayed(output_msg, "Anchorpoint Success", 'INFO')
        except subprocess.CalledProcessError as e:
            print(f"Anchorpoint Error: An error occurred during execution: {e}")
            show_message_delayed("An error occurred during execution", "Anchorpoint Error", 'ERROR')
        except Exception as e:
            print(f"Anchorpoint Error: Unexpected error: {str(e)}")
            show_message_delayed(f"Unexpected error: {str(e)}", "Anchorpoint Error", 'ERROR')

    threading.Thread(target=execute_command).start()

class ANCHORPOINT_OT_show_message(Operator):
    """Show a message dialog"""
    bl_idname = "anchorpoint.show_message"
    bl_label = "File published successfully"
    
    message: StringProperty(
        name="Message",
        description="Message to display",
        default=""
    )
    
    dialog_title: StringProperty(
        name="Dialog Title",
        description="Title for the dialog",
        default="Anchorpoint"
    )
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # restore cursor to default
        context.window.cursor_modal_restore()
        # show success dialog
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        # Split message into lines for better display
        lines = self.message.split('\n')
        for line in lines:
            if line.strip():
                layout.label(text=line)


class ANCHORPOINT_OT_open_anchorpoint(Operator):
    """Open Anchorpoint application with the current file"""
    bl_idname = "anchorpoint.open_anchorpoint"
    bl_label = "Open Anchorpoint"
    bl_description = "Opens Anchorpoint application"
    
    def execute(self, context):
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Document must be saved before opening Anchorpoint.")
            return {'CANCELLED'}
        
        file_path = bpy.data.filepath
        try:
            if platform.system() == "Windows":
                # Use the user's home directory for AppData
                appdata = os.getenv('LOCALAPPDATA')
                anchorpoint_exe = os.path.join(
                    appdata, "Anchorpoint", "anchorpoint.exe")
                if not os.path.exists(anchorpoint_exe):
                    self.report({'ERROR'}, "Anchorpoint executable not found!")
                    return {'CANCELLED'}
                subprocess.Popen([anchorpoint_exe, file_path], shell=False)
            elif platform.system() == "Darwin":
                # On Mac, use the same directory as the CLI
                anchorpoint_app = "/Applications/Anchorpoint.app/Contents/MacOS/Anchorpoint"
                if not os.path.exists(anchorpoint_app):
                    self.report({'ERROR'}, "Anchorpoint app not found!")
                    return {'CANCELLED'}
                subprocess.Popen([anchorpoint_app, file_path])
            else:
                self.report({'ERROR'}, "Unsupported OS")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open Anchorpoint: {e}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class ANCHORPOINT_OT_publish_version(Operator):
    """Publish current version to Anchorpoint"""
    bl_idname = "anchorpoint.publish_version"
    bl_label = "Publish"
    bl_description = "Sets your current file as latest version"
    
    comment: StringProperty(
        name="Comment",
        description="Comment for this version",
        default=""
    )
    
    def execute(self, context):
        if not self.comment.strip():
            self.report({'ERROR'}, "Please enter a comment")
            return {'CANCELLED'}
        
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Document must be saved before publishing.")
            return {'CANCELLED'}
        
        file_path = bpy.data.filepath
        if not is_in_anchorpoint_project(file_path):
            self.report({'ERROR'}, "This file is not part of an Anchorpoint project")
            return {'CANCELLED'}
        
        # Set cursor to waiting/hourglass
        context.window.cursor_modal_set('WAIT')
        
        # Start the publish process
        run_executable(self.comment, file_path)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "You have to save your file first")
            return {'CANCELLED'}
        
        file_path = bpy.data.filepath
        if not is_in_anchorpoint_project(os.path.dirname(file_path)):
            self.report({'ERROR'}, "This file is not part of an Anchorpoint project")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self, width=400, confirm_text="Publish")
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Publishing will create a new version in Anchorpoint")
        layout.prop(self, "comment", text="Comment")


class ANCHORPOINT_MT_menu(bpy.types.Menu):
    """Anchorpoint menu"""
    bl_label = "Anchorpoint"
    bl_idname = "ANCHORPOINT_MT_menu"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("anchorpoint.open_anchorpoint", icon='FILE_FOLDER')
        layout.operator("anchorpoint.publish_version", icon='EXPORT')


def draw_anchorpoint_menu(self, context):
    """Draw Anchorpoint menu in the header"""
    self.layout.menu("ANCHORPOINT_MT_menu")


classes = [
    ANCHORPOINT_OT_show_message,
    ANCHORPOINT_OT_open_anchorpoint,
    ANCHORPOINT_OT_publish_version,
    ANCHORPOINT_MT_menu,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add menu to the header
    bpy.types.TOPBAR_MT_editor_menus.append(draw_anchorpoint_menu)


def unregister():
    # Remove menu from the header
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_anchorpoint_menu)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
