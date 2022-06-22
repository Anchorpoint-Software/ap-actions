import anchorpoint as ap

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    print("on_is_action_enabled called for ", path, type)
    return True

# This check is required to avoid script execution when Anchorpoint loads the on_is_action_enabled function
# It is best practice to always guard your script with this syntax. Learn more here: https://www.geeksforgeeks.org/what-does-the-if-__name__-__main__-do/
if __name__ == "__main__":
    dialog = ap.Dialog()
    dialog.title = "on_is_action_enabled example trigger"
    dialog.add_text("This action is enabled by implementing the <b>on_is_action_enabled</b> callback")
    dialog.show()