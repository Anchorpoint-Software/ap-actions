import os
import platform
import sys

def get_ap_dataroot():
    '''
    Returns the root of the AppData / Application Support folder for Anchorpoint
    '''
    if platform.system() == "Windows":
        return os.getenv('APPDATA') + "/Anchorpoint Software/Anchorpoint/"
    else: 
        return "~/Library/Application Support/Anchorpoint Software/Anchorpoint/"

def get_ap_root():
    '''
    Returns the root of the Anchorpoint installation. Can be overwritten with the ANCHORPOINT_ROOT environment variable
    '''
    if "ANCHORPOINT_ROOT" in os.environ:
        root = os.environ["ANCHORPOINT_ROOT"]
    elif platform.system() == "Windows":
        folder = os.getenv('APPDATA') + "/../Local/Anchorpoint/"
        directories = [item for item in os.listdir(folder) if item.startswith("app-")]
        directories.sort()
        root = os.path.join(folder, directories[-1])
    else: 
        root = "/Applications/Anchorpoint.app"
    
    if not os.path.exists(root):
        raise RuntimeError("No valid installation of Anchorpoint found. Please install from anchorpoint.app")

    return root

def get_ap_pythonlibs_root():
    '''
    Returns the root of the Anchorpoint built-in python libraries
    '''
    root = get_ap_root()
    if platform.system() == "Windows":
        root = os.path.join(root, "plugins/python/Lib/site-packages")
    else:
        root = os.path.join(root, "Contents/Resources/python/lib/python3.9/site-packages")

    if not os.path.exists(root):
        raise RuntimeError("No valid installation of Anchorpoint found. Please install from anchorpoint.app")

    return root

def get_qt_application():
    '''
    Returns the running instance of QApplication - or creates a new one
    '''
    from PySide2.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    return app

if __name__ == '__main__':
    app = get_qt_application()