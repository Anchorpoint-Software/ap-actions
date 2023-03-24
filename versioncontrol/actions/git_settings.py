import anchorpoint as ap
import apsync as aps

def refresh_timeline(dialog):
    dialog.store_settings()
    ap.vc_load_pending_changes("Git", False)

class GitSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.dialog = ap.Dialog()
        self.dialog.add_switch(True, var="autopush", text="Combine Commit and Push", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will automatically push your changes to the remote Git repository")
        self.dialog.load_settings(self.get_settings())


    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitSettings")
    
    def auto_push_enabled(self):
        return self.get_settings().get("autopush", True)
    

def on_show_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)