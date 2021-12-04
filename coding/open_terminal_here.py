import anchorpoint as ap
import os
import platform

ctx = ap.Context.instance()

if platform.system() == "Darwin":
    os.system(f"open -a Terminal {ctx.path}")
elif platform.system() == "Windows":
    os.system(f"start cmd /k cd {ctx.path}")