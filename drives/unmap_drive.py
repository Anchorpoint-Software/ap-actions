import anchorpoint as ap
import apsync as aps
import platform
import subprocess
import os
from os import path

ctx = ap.get_context()
ui = ap.UI()

drive_var = "drive"

def remove_bat_file(drive):    
    app_data = os.getenv('APPDATA')
    startup_path = f'{app_data}/Microsoft/Windows/Start Menu/Programs/Startup'
    path_to_bat = path.join(startup_path,"ap_mount_"+drive[:-1]+".bat")
    if(path.isfile(path_to_bat)):
        os.remove(path_to_bat)

def get_used_drives():
    subst = subprocess.run(
        [
            "subst"
        ], capture_output=True
    )

    if subst.returncode == 0:
        return subst.stdout.splitlines()
    return []

def unmount(dialog):
    drive = dialog.get_value(drive_var)
    drive = drive[0:2]

    subst = subprocess.run(
        [
            "subst",
            f"{drive}",
            "/D"
        ]
    )

    if subst.returncode != 0:
        print(subst.stderr)
        ui.show_error("Failed to Unmount!")
    else:
        print(subst.stdout)
        ui.show_success("Unmount Successful")

    remove_bat_file(drive)
    dialog.close()

def show_options():
    drives = get_used_drives()
    if len(drives) == 0:
        ui.show_error("No drives to unmount", "Mount another drive first")
        return

    dialog = ap.Dialog()
    dialog.title = "Unmap Drive"

    if ctx.icon:
        dialog.icon = ctx.icon

    dialog.add_text("Unmap Drive:\t").add_dropdown(drives[-1], drives, var=drive_var)
    dialog.add_button("Unmap", callback=unmount)

    dialog.show()

if platform.system() == "Darwin":
    ui.show_error("Unsupported Action", "This action is only supported on Windows :-(")
else:
    show_options()