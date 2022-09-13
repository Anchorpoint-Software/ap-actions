from cgitb import enable
import anchorpoint as ap
import apsync as aps
import os
import shutil, platform

import rclone_install_helper as rclone_install

ctx = ap.Context.instance()
ui = ap.UI()
settings = aps.Settings("rclone")

def isWin():
    if platform.system() == "Windows":
        return True
    return False

def store_settings(dialog : ap.Dialog):
    cache_path = dialog.get_value("cache_var")
    if(cache_path!=settings.get("cachepath")):
        settings.set("cachepath",cache_path)
        settings.store()
        ui.show_success("Cache location changed")
        dialog.close()

def clear_cache(dialog : ap.Dialog):
    settings = aps.Settings("rclone")    
    cache_path = settings.get("cachepath",default=get_default_cache_path())

    vfs_path = os.path.join(cache_path,"vfs")
    vfs_metaPath = os.path.join(cache_path,"vfsMeta")

    if os.path.isdir(vfs_path):
        shutil.rmtree(vfs_path)

    if os.path.isdir(vfs_metaPath):
        shutil.rmtree(vfs_metaPath)

    ui.show_success("Cache cleared")
    dialog.close()

def get_default_cache_path():
    if isWin():
        app_data_roaming = os.getenv('APPDATA')
        app_data = os.path.abspath(os.path.join(app_data_roaming, os.pardir))
        return os.path.join(app_data,"Local/rclone").replace("/","\\")
    else: 
        cache_path = os.path.normpath(os.path.expanduser("~/library/caches/anchorpoint software/anchorpoint/rclone"))
        if not os.path.exists(cache_path): 
            os.mkdir(cache_path)
        return cache_path

def open_dialog():    
    cache_path = settings.get("cachepath")

    if cache_path == "":
        cache_path = get_default_cache_path()

    try:
        is_not_empty = len(os.listdir(cache_path)) != 0
    except:
        is_not_empty = False

    dialog = ap.Dialog()
    dialog.title = "Cloud Drive Settings"
    dialog.add_text("Cache Location").add_input(cache_path, browse=ap.BrowseType.Folder, var="cache_var")

    if ctx.icon:
        dialog.icon = ctx.icon    

    dialog.add_button("Apply", callback=store_settings).add_button("Clear Cache", callback=clear_cache, enabled = is_not_empty)
    dialog.show()


ctx.run_async(rclone_install.check_winfsp_and_rclone, open_dialog)
