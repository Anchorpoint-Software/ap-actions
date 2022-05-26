import unreal

# captures a high res screenshot
class capture(object):
    def __init__(self):
        unreal.EditorLevelLibrary.editor_set_game_view(True)
        self.actors = (actor for actor in unreal.EditorLevelLibrary.get_selected_level_actors())
        shot_name = "test"
        unreal.AutomationLibrary.take_high_res_screenshot(1920,1080, shot_name + ".png")
        
# returns an array of the selected assets
def get_selected_assets():
    utility_base = unreal.GlobalEditorUtilityBase.get_default_object()
    return utility_base.get_selected_assets()

def get_asset_infos():
    selectedAssets = get_selected_assets()
    
    for asset in selectedAssets:
        print(asset.get_full_name())
        print(asset.get_fname())
        print(asset.get_path_name())

get_asset_infos()
capture()