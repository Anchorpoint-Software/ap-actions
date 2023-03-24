import anchorpoint as ap
import apsync as aps

class GitSettings(ap.AnchorpointSettings):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.dialog = ap.Dialog()

    def get_dialog(self):         
        return self.dialog
    

def on_show_preferences(settings_list, ctx: ap.Context):
    gitSettings = GitSettings(ctx)
    gitSettings.name = 'Git'
    gitSettings.priority = 100
    gitSettings.icon = ":/icons/versioncontrol.svg"
    settings_list.add(gitSettings)