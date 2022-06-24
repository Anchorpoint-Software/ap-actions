import os
import shutil
import apsync as aps
import anchorpoint as ap

ctx = ap.Context.instance()
drive = ctx.path[0]

def kill_rclone():
    settings = aps.Settings("drive settings")
    pid = settings.get(drive)
    settings.remove(drive)
    settings.store()
    os.system("taskkill /PID {}".format(pid))

kill_rclone()

print(shutil.which("WinFsp"))