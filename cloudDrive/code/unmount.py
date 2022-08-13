import os
import platform
import apsync as aps
import anchorpoint as ap

def kill_rclone():
    if platform.system() == "Windows":
        os.system("taskkill /im rclone.exe")
    else:
        os.system("umount /Volumes/Anchorpoint")

def remove_auto_mount():
    ctx = ap.Context.instance()
    local_settings = aps.Settings(ctx.workspace_id)
    local_settings.remove("rclone-automount")
    local_settings.remove("rclone-drive")
    local_settings.store()

kill_rclone()
remove_auto_mount()