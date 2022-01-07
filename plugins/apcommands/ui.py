from typing import Optional

def get_qt_application(style: Optional[str] = None):
    from PySide2.QtWidgets import QApplication
    import os
    os.environ['QT_MAC_WANTS_LAYER'] = '1'

    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(sys.argv)
    
    if style:
        app.setStyleSheet(style)

    return app

def get_style(path_to_sheet: Optional[str] = None):
    if not path_to_sheet:
        import qdarkstyle
        import os
        dirname = os.path.dirname(__file__)
        path_to_sheet = os.path.join(dirname, "style.qss")
    
    with open(path_to_sheet) as file:
        return file.read()