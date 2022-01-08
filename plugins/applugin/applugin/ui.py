from typing import Optional

def get_qt_application():
    from PySide2.QtWidgets import QApplication
    import os
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(sys.argv)
    
    return app