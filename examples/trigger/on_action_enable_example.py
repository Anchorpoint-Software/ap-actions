import anchorpoint as ap

def on_action_enable(path: str, ctx: ap.Context) -> bool:
    print("on_action_enable called for ", path)
    return True

# This check is required to avoid script execution when Anchorpoint loads the on_action_enabled function
# It is best practice to always guard your script with this syntax. Learn more here: https://www.geeksforgeeks.org/what-does-the-if-__name__-__main__-do/
if __name__ == "__main__":
    dialog = ap.Dialog()
    dialog.title = "on_action_enable example trigger"
    dialog.add_text("This action is enabled by implementing the <b>on_action_enable</b> callback")
    dialog.show()