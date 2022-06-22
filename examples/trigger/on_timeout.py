import anchorpoint as ap

def on_timeout(ctx: ap.Context):
    print(f"action called from time trigger {ctx}")
    print(f"Selected: {ctx.selected_folders} {ctx.selected_files}")