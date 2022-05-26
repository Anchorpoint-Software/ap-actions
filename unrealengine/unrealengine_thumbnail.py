import unreal

def get_selected_assets():
    utility_base = unreal.GlobalEditorUtilityBase.get_default_object()
    return utility_base.get_selected_assets()

selectedAssets = get_selected_assets()

for asset in selectedAssets:
    print(asset.get_full_name())
    print(asset.get_fname())
    print(asset.get_path_name())
