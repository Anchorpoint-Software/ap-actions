import os
import platform
import sys

def initialize():
    '''
    Must be called once to setup PATH to find and load PySide2 and other Anchorpoint dependencies
    '''

    try:
        # We are trying to import a PySide2 dependency to see if it is already available
        from PySide2.QtWidgets import QApplication
    except:
        # If not, we load the Anchorpoint provided PySide2 module
        __resolve_pyside2()
        from PySide2.QtWidgets import QApplication

    __load_cdll(get_ap_root(), "libsync.dylib", "sync.dll")

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

def __load_cdll(ap_root: str, namedarwin: str, namewin: str):
    import ctypes
    if platform.system() == "Windows":
        ctypes.CDLL(os.path.join(ap_root, namewin))
    elif platform.system() == "Darwin":
        ctypes.CDLL(os.path.join(ap_root, f"Contents/Frameworks/{namedarwin}"), mode=os.RTLD_LAZY)

def __load_qtdll(ap_root: str, name: str):
    import ctypes
    if platform.system() == "Windows":
        ctypes.CDLL(os.path.join(ap_root, f"{name}.dll"))
    elif platform.system() == "Darwin":
        ctypes.CDLL(os.path.join(ap_root, f"Contents/Frameworks/{name}.framework/Versions/5/{name}"), mode=os.RTLD_LAZY)

__ap_pyside2_resolved = False
def __resolve_pyside2():
    global __ap_pyside2_resolved
    if __ap_pyside2_resolved:
        return

    ap_root = get_ap_root()
    ap_pythonlibs_root = get_ap_pythonlibs_root()
    sys.path.insert(0, ap_pythonlibs_root)

    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    if platform.system() == "Darwin":
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(ap_root, "Contents/PlugIns")
    else:
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ap_root
    libs = [
        "QtWidgets", "QtDBus", "QtPrintSupport", "QtCore", "QtGui", "QtQml"
    ] if platform.system() == "Darwin" else [
        "Qt5Widgets", "Qt5Core", "Qt5Gui", "Qt5Qml", "Python3"
    ] 

    for lib in libs:
        __load_qtdll(ap_root, lib)

    __ap_pyside2_resolved = True


def get_qt_application():
    initialize()
    from PySide2.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    return app

if __name__ == '__main__':
    app = get_qt_application()