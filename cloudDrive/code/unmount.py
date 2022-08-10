import os
import shutil
import platform

def kill_rclone():
    if platform.system() == "Windows":
        os.system("taskkill /im rclone.exe")
    else:
        os.system("umount /Volumes/Anchorpoint")

kill_rclone()