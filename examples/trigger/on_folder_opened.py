import anchorpoint as ap
import time

def on_folder_opened(ctx: ap.Context):
    print(f"action called from folder opened trigger {ctx.path}")