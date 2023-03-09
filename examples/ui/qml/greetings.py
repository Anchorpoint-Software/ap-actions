# This example works with the Anchorpoint provided anchorpoint and PySide2 module.
# This is an advanced example where we use QML from PySide2 to display a native looking greetings Dialog to the user.
# Note that Anchorpoint internally uses QML for a nice UX experience.
# If you just want to create a simple Dialog, check the simple.yaml action

import anchorpoint as ap
from PySide2.QtWidgets import QApplication
from PySide2.QtQuick import QQuickWindow
from PySide2.QtCore import QUrl, QObject, QMetaObject, Slot
from PySide2.QtQml import QQmlComponent

# Anchorpoint UI class allows us to show e.g. Toast messages in Anchorpoint
ui = ap.UI()

# The Anchorpoint context object provides the predefined variables and the inputs from the YAML file.
ap_context = ap.get_context()
yaml_dir = ap_context.yaml_dir

# We create a controller class that inhertis from QObject.
# The controller class is providing 'slots' that can be called from the QML file
class Controller(QObject):
    @Slot(str)
    def greetings(self, name):
        # Called from QML. Shows a 'success' toast in anchorpoint.
        ui.show_info(f"Hello {name}")


# First, we check if we can access the Anchorpoint provided QApplication instance
app = QApplication.instance()
if app is None:
    # Ouch, no Anchorpoint QApplication instance, this is not good.
    # We show a toast in Anchorpoint and exit the script
    import sys

    ui.show_error(
        "PySide2 hiccup",
        description="QApplication could not be accessed, please report a bug.",
    )
    sys.exit()

# Instantiate our handy controller object
controller = Controller()

# Everything OK, we can access the active QML Engine from the Anchorpoint UI.
engine = ui.get_qml_engine()
if engine is None:
    ui.show_error(
        "PySide2 hiccup",
        description="No QQmlApplicationEngine found, please report a bug.",
    )
    exit()

# The QML context object used by Anchorpoint.
engine_context = engine.rootContext()

# The Anchorpoint root QQuickWindow
window = engine.rootObjects()[0]

# Load our QML file from the yaml directory.
component = QQmlComponent(engine, QUrl.fromLocalFile(f"{yaml_dir}/dialog.qml"))
if component.status() != QQmlComponent.Ready:
    # QML parsing error, see ap.log
    print(f"QML errors: {component.errors()}", flush=True)
    ui.show_error(
        "QML error",
        description="QML file has errors. See ap.log for details.",
    )
    exit()

# When creating the QML object from our QML file, we have to provide initial properties.
# First, we provide the parent object (the main window) so that Anchorpoint knows where to
# show our QML dialog.
# Second, we pass our controller object so that QML can call our python script again.
initial_properties = {"parent": window.contentItem(), "controller": controller}
qml_object = component.createWithInitialProperties(initial_properties, engine_context)

# Tell the controller object about our QML object as well.
controller.qmlObject = qml_object

# It is essential to parent our QMLComponent instance to the controller so that
# the instance is destroyed when the controller cleanup slot is called from QML.
qml_object.setParent(controller)

# Last but not least we have to call the "openDialog" QML method that brings up our fancy dialog.
QMetaObject.invokeMethod(qml_object, "openDialog")
