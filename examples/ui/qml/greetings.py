import anchorpoint as ap
from PySide2.QtWidgets import QApplication
from PySide2.QtQuick import QQuickWindow
from PySide2.QtCore import QUrl, QObject, QMetaObject, Slot
from PySide2.QtQml import QQmlComponent

ui = ap.UI()

class Controller(QObject):    
    @Slot(str)
    def greetings(self, name):
        ui.showToast(f"Hello {name}")

    @Slot()
    def cleanup(self):
        self.context.setContextProperty("controller", None)

app = QApplication.instance()
if app is None:
    import sys
    ui.showToast("PySide2 hiccup", \
        ap.UI.ToastType.Info, \
        description="QApplication could not be accessed, please report a bug.")
    app = QApplication(sys.argv)
    sys.exit(app.exec_())
else:
    engine = ui.getQmlEngine()
    if engine is None:
        ui.showToast("PySide2 hiccup", \
        ap.UI.ToastType.Info, \
        description="No QQmlApplicationEngine found, please report a bug.")
        exit()
    
    apContext = ap.Context.instance()
    
    engineContext = engine.rootContext()
    root = engine.rootObjects()[0]

    controller = Controller()
    controller.context = engineContext

    component = QQmlComponent(engine, QUrl.fromLocalFile(f"{apContext.yamlDir}/dialog.qml"))
    if (component.status() is not QQmlComponent.Ready):
        print(f"QML errors: {component.errors()}", flush=True)
        ui.showToast("QML error", \
            ap.UI.ToastType.Fail, \
            description="QML file has errors. See ap.log for details.")
        exit()
        
    initialProperties = {"parent": root.contentItem(), "controller": controller}

    object = component.createWithInitialProperties(initialProperties, engineContext)
    
    # It is essential to parent our QMLComponent instance to the controller so that
    # the instance is destroyed when the controller cleanup slot is called from QML.
    object.setParent(controller) 

    QMetaObject.invokeMethod(object, "openDialog")




