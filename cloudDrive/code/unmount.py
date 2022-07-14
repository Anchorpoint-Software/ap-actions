import os
import shutil

def kill_rclone():
    os.system("taskkill /im rclone.exe")

kill_rclone()

print(shutil.which("WinFsp"))