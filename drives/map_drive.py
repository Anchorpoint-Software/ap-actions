import anchorpoint as ap
import apsync as aps
import platform
import subprocess
import os

ctx = ap.Context.instance()
ui = ap.UI()

drive_var = "drive"

def get_unused_drives():
    import string
    from ctypes import windll

    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if not bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives

def mount(dialog):
    drive = dialog.get_value(drive_var)

    subst = subprocess.run(
        [
            "subst",
            f"{drive}:",
            f"{ctx.path}"
        ]
    )

    if subst.returncode != 0:
        print(subst.stderr)
        ui.show_error("Failed to Mount!")
    else:
        print(subst.stdout)
        ui.show_success("Mount Successful")

    dialog.close()

def show_options():
    drives = get_unused_drives()
    if len(drives) == 0:
        ui.show_error("No drives to mount", "Unmount another drive first")
        return

    dialog = ap.Dialog()
    dialog.title = "Map Folder as Drive"

    dialog.add_text("Map to Drive:\t").add_dropdown(drives[-1], drives, var=drive_var)
    dialog.add_button("Map", callback=mount)

    dialog.show()

if platform.system() == "Darwin":
    ui.show_error("Unsupported Action", "This action is only supported on Windows :-(")
else:
    show_options()