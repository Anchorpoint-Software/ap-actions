import anchorpoint as ap
import os
import platform

ctx = ap.get_context()
if platform.system() == "Darwin":
    os.system(f"open -a Terminal \"{ctx.path}\"")
elif platform.system() == "Windows":
    os.system(f"start cmd /k cd \"{ctx.path}\"")