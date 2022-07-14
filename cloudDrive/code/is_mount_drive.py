import anchorpoint as ap
import apsync as aps

# checks if the selected drive is a clouddrive
def on_is_action_enabled(drive: str, type: ap.Type, ctx: ap.Context) -> bool:
    if drive == "":
        return False
    
    settings = aps.Settings("drive settings")
    drive_settings = settings.get(drive[0])

    if drive_settings == "":
        return False
    
    return True

if __name__ == "__main__":
    dialog = ap.Dialog()
    dialog.title = "on_is_action_enabled example trigger"
    dialog.add_text("This action is enabled by implementing the <b>on_is_action_enabled</b> callback")
    dialog.show()