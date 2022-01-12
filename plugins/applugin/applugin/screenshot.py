from applugin import core
if __name__ == '__main__':
    core.initialize()

from PySide2.QtGui import QCursor, QKeyEvent, QMouseEvent, QPixmap
from PySide2.QtWidgets import QApplication, QDialog, QRubberBand
from PySide2.QtCore import QSize, Qt, QEvent, QPoint, QRect, Signal
import platform

class ScreenshotDialog(QDialog):

    image_captured = Signal(QPixmap)

    def __init__(self, parent=None):
        super(ScreenshotDialog, self).__init__(parent)

        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)
        self.rubberorigin = QPoint()

        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.6)

        self.setGeometry(QApplication.desktop().screenGeometry(self))
        QApplication.setOverrideCursor(Qt.CrossCursor)

        self.setFocus()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def showEvent(self, event):
        self.setFocus()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        super().showEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        window = self.windowHandle()
        if window:
            currentscreen = window.screen()
            hoveredscreen = QApplication.screenAt(QCursor.pos())

            if hoveredscreen and currentscreen != hoveredscreen:
                window.setScreen(hoveredscreen)
                self.show()
                self.setGeometry(window.screen().geometry())

        super().leaveEvent(event) 
        
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Tab:
            window = self.windowHandle()
            if window:
                currentscreen = window.screen()
                if currentscreen:
                    screens = QApplication.screens()
                    if len(screens) > 1:
                        index = screens.index(currentscreen)
                        if index >= 0:
                            if index >= len(screens) - 1:
                                window.setScreen(screens[0])
                            else:
                                window.setScreen(screens[index + 1])
                            self.show()
                            self.setGeometry(window.screen().geometry())
        else:
            QApplication.restoreOverrideCursor()
            self.reject()

        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.rubberorigin = event.pos()
            self.rubberband.setGeometry(QRect(self.rubberorigin, QSize()))
            self.rubberband.show()
        else:
            QApplication.restoreOverrideCursor()
            self.reject()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.rubberband.isVisible():
            self.rubberband.setGeometry(QRect(self.rubberorigin, event.pos()).normalized())

        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self.rubberband:
                self.rubberband.hide()

                window = self.windowHandle()
                if window:
                    screen = window.screen()
                    if screen:
                        geometry = screen.geometry()
                        scalefactor = 1.0 / screen.devicePixelRatio() if platform.system() == "Windows" else 1.0
                        
                        # normalize the origin point to be always top left of the rubberband regardless where the user started to select
                        origin = self.rubberorigin
                        if self.rubberorigin.x() > event.x() and self.rubberorigin.y() > event.y():
                            origin = event.pos()
                        elif self.rubberorigin.x() > event.x():
                            origin.setX(event.x())
                        elif self.rubberorigin.y() > event.y():
                            origin.setY(event.y())

                        # calculate the capture rect, keep in mind different monior setups
                        capturerect = QRect(origin.x() + geometry.x() * scalefactor, origin.y() + geometry.y() * scalefactor, 
                                            self.rubberband.rect().width(), self.rubberband.rect().height()).normalized()
                                    
                        # make this window fully transparent to grab everything behind
                        self.setWindowOpacity(0)
                        QApplication.instance().processEvents()

                        pix = screen.grabWindow(QApplication.desktop().winId(), capturerect.x(), capturerect.y(), capturerect.width(), capturerect.height())
                        self.image_captured.emit(pix)
                
                QApplication.restoreOverrideCursor()
                self.accept()


        super().mouseReleaseEvent(event)


def store_screenshot(img: QPixmap):
    import os
    directory, _ = os.path.split(__file__)
    fn = os.path.join(directory, "screenshot.png")
    img.save(fn)

if __name__ == '__main__':
    import sys
    app = core.get_qt_application()
    window = ScreenshotDialog()
    window.show()

    window.image_captured.connect(store_screenshot)

    sys.exit(app.exec_())