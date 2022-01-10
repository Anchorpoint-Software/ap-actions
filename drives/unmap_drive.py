import anchorpoint as ap
import apsync as aps
import platform
import subprocess
import os

ctx = ap.Context.instance()
ui = ap.UI()

drive_var = "drive"

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

    dialog.close()

def show_options():
    drives = get_used_drives()
    if len(drives) == 0:
        ui.show_error("No drives to unmount", "Mount another drive first")
        return

    dialog = ap.Dialog()
    dialog.title = "Unmap Drive"

    dialog.add_text("Unmap Drive:\t").add_dropdown(drives[-1], drives, var=drive_var)
    dialog.add_button("Unmap", callback=unmount)

    dialog.show()

if platform.system() == "Darwin":
    ui.show_error("Unsupported Action", "This action is only supported on Windows :-(")
else:
    show_options()