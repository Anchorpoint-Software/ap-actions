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
        self.dialog.add_switch(True, var="autolock", text="Automatically lock changed files", callback=lambda d,v: refresh_timeline(d))
        self.dialog.add_info("Anchorpoint will lock all binaries that have been modified. Locks will be released when the commits are pushed to the remote Git repository. <br><a href='https://docs.anchorpoint.app/docs/3-work-in-a-team/projects/5-File-locking/#git-projects'>Learn about File Locking</a>")
        self.dialog.add_switch(True, var="notifications", text="Show notifications for new commits")
        self.dialog.add_info("Show a system notification when new commits are available on the remote Git repository")
        self.dialog.load_settings(self.get_settings())


    def get_dialog(self):         
        return self.dialog
    
    def get_settings(self):
        return aps.Settings("GitSettings")
    
    def auto_push_enabled(self):
        return self.get_settings().get("autopush", True)
    
    def auto_lock_enabled(self):
        return self.get_settings().get("autolock", True)
    
    def notifications_enabled(self):
        return self.get_settings().get("notifications", True)
    

def on_show_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)