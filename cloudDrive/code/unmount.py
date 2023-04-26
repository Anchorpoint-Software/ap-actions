import os
import platform
import apsync as aps
import anchorpoint as ap

def kill_rclone():
    if platform.system() == "Windows":
        os.system("taskkill /IM rclone.exe /F")
    else:
        # try diskutil unmount first
        r = os.system("diskutil unmount /Volumes/Anchorpoint")
        if r == 0:
            return
        
        # on error try killall
        os.system("killall rclone")

    ap.UI().reload_drives()

def remove_auto_mount(ctx: ap.Context):
    local_settings = aps.Settings(ctx.workspace_id)
    local_settings.remove("rclone-automount")
    local_settings.remove("rclone-drive")
    local_settings.store()

def on_removed_from_workspace(ctx: ap.Context):
    kill_rclone()
    remove_auto_mount(ctx)    
    local_settings = aps.Settings("rclone")
    local_settings.clear()
    local_settings.store()

if __name__ == "__main__":
    kill_rclone()
    remove_auto_mount(ap.get_context())