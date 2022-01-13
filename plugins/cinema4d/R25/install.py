import platform
import os
import sys
import ctypes
from distutils.dir_util import copy_tree

class Plugin:
    '''
    Class that represents a DCC Plugin, used by Anchorpoint for installation of the plugin.
    Must be named Plugin so that Anchorpoint can find it.
    '''
    def get_description(self):
        return {
            "name": "Cinema 4D",
            "version": "R25",
        }

    def get_application_location(self):
        '''
        Returns the installation path of the Application.
        '''
        if platform.system() == "Windows":
            path = "C:/Program Files/Maxon Cinema 4D R25"
        elif platform.system() == "Darwin":
            path = "/Applications/Maxon Cinema 4D R25"

        return path

    def is_installed(self, app_location):
        '''
        Checks whether or not the plugin is already installed
        '''
        return os.path.exists(os.path.join(app_location, "plugins/anchorpoint/install.py"))

    def install(self, app_location):
        '''
        Installs the plugin for the Application. 
        '''
        if not os.path.exists(app_location):
            raise RuntimeError("Cannot install plugin, path does not exist: " + app_location)
        
        # Copy content of plugin to maxons plugin location
        dir, _ = os.path.split(__file__)
        plugin_dir = os.path.join(app_location, "plugins/anchorpoint")
        os.makedirs(plugin_dir, exist_ok=True)
        os.makedirs(os.path.join(plugin_dir, "res"), exist_ok=True)
        copy_tree(dir, plugin_dir)
        
        # Copy applugin as well
        copy_tree(os.path.join(dir, "../../applugin/applugin"), os.path.join(plugin_dir, "applugin"))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Location of Cinema 4D must be provided")
        exit()

    def is_admin():
        if platform.system() == "Darwin":
            # TODO
            return True
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if is_admin():            
        plugin = Plugin() 
        plugin.install(sys.argv[1])
    else:
        # Re-run the program with admin rights
        if platform.system() == "Darwin":
            # TODO
            raise NotImplementedError
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f"\"{sys.argv[0]}\" \"{sys.argv[1]}\"", None, 1)