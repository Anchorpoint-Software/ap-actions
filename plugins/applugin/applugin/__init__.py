import os
import ctypes
import platform
import sys
from . import core

def __initialize():
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

    __load_cdll(core.get_ap_root(), "libsync.dylib", "sync.dll")

def __load_cdll(ap_root: str, namedarwin: str, namewin: str):
    if platform.system() == "Windows":
        ctypes.CDLL(os.path.join(ap_root, namewin))
    elif platform.system() == "Darwin":
        ctypes.CDLL(os.path.join(ap_root, f"Contents/Frameworks/{namedarwin}"), mode=os.RTLD_LAZY)

def __load_qtdll(ap_root: str, name: str):
    if platform.system() == "Windows":
        ctypes.CDLL(os.path.join(ap_root, f"{name}.dll"))
    elif platform.system() == "Darwin":
        ctypes.CDLL(os.path.join(ap_root, f"Contents/Frameworks/{name}.framework/Versions/5/{name}"), mode=os.RTLD_LAZY)

def __resolve_pyside2():
    ap_root = core.get_ap_root()
    ap_pythonlibs_root = core.get_ap_pythonlibs_root()
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
        
__initialize()
from . import * 