import os
import shutil
import apsync as aps

def kill_rclone():
    os.system("taskkill /im rclone.exe")


kill_rclone()

print(shutil.which("WinFsp"))