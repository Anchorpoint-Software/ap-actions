import anchorpoint as ap
import apsync as aps

import os
import sys
import subprocess
import sys

ctx = ap.Context.instance()
ui = ap.UI()

def load_plugin(plugin_path):
    root = os.path.split(plugin_path)[0]
    sys.path.insert(0, root)
    try:
        from install import Plugin
        p = Plugin()
    except Exception as e:
        p = None
        print(e)
    sys.path.pop(0)  
    return p

def get_available_plugin_paths():
    plugins = []
    directory, _ = os.path.split(__file__)
    for root, _, files in os.walk(directory):
        for file in files:
            if file == "install.py":
                plugins.append(os.path.join(root, file))

    return plugins

def install_plugin(dialog, i, plugin, plugin_path):
    name = plugin.get_description()["name"]
    version = plugin.get_description()["appversion"]
    location = dialog.get_value(f"location{i}")
    try:
        # must run as separate process as admin rights might be required
        result = subprocess.run([sys.executable, plugin_path, location])
        if result.returncode != 0:
            ui.show_error("Could not install plugin", "See Console Log")
        else:
            ui.show_success("Plugin installed successfully")
            dialog.set_value(f"button{i}", "Update Plugin")

            settings = aps.Settings()
            settings.set(name+version, location)
            settings.store()
    except Exception as e:
        ui.show_error("Could not install plugin", str(e))

def show_options():
    plugin_paths = get_available_plugin_paths()
    if len(plugin_paths) == 0:
        ui.show_error("No plugins to install")
        return

    settings = aps.Settings()

    dialog = ap.Dialog()
    dialog.icon = ctx.icon
    dialog.title = "Install Plugin"

    for i, path in enumerate(plugin_paths):
        plugin = load_plugin(path)
        if plugin:
            location = plugin.get_application_location()
            desc = plugin.get_description()
            name = desc["name"]
            version = desc["appversion"]

            installed_location = settings.get(name+version, default=location)

            if i > 0: dialog.add_separator()
            dialog.add_text(f"{name} {version}")
            dialog.add_text("Location:\t").add_input(installed_location, browse=ap.BrowseType.Folder, var=f"location{i}")
            
            if plugin.is_installed(installed_location):
                dialog.add_button("Update Plugin", var=f"button{i}", callback=lambda d, src=i: install_plugin(d, src, plugin, path))
            else: 
                dialog.add_button("Install Plugin", var=f"button{i}", callback=lambda d, src=i: install_plugin(d, src, plugin, path))

    dialog.show()

show_options()