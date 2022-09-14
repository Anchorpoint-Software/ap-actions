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

#get_asset_infos()
#capture()

def test():
    print(unreal.EditorLevelLibrary.get_editor_world())
    actors = unreal.GameplayStatics.get_all_actors_of_class(unreal.EditorLevelLibrary.get_editor_world(), unreal.StaticMeshActor) # change this later to all actors? unreal.Actor
    #for x in actors:
     #   print(x)
     
    actor = actors[3]
    print(actor.get_full_name())
    print(actor.get_fname())
    print(actor.get_path_name())
    print(actor.get_folder_path())
    print("folder path: ", actor.get_folder_path())
    
    static_comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    path_string = static_comp.get_editor_property('static_mesh').get_path_name()
    
    print('path', path_string)
     
    
test()