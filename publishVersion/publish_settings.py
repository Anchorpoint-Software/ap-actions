import anchorpoint as ap
import apsync as aps
import sys
import publish

ctx = ap.Context.instance()
project = aps.get_project(ctx.path)
ui = ap.UI()
if project is None:
    ui.show_info("Action only works with projects")
    sys.exit(0)

settings = project.get_metadata()


def store_settings_and_run(dialog):
    settings["publish_version_appendix"] = dialog.get_value("appendix_var")
    settings["checkbox"] = str(dialog.get_value("checkbox_var"))
    if dialog.get_value("checkbox_var") is True:
        settings["publish_file_location"] = dialog.get_value("location_var")
    else:
        settings["publish_file_location"] = ""

    try:
        project.update_metadata(settings)
    except Exception as e:
        ui.show_info(f"Cannot store settings","You need proper project permissions to store the settings")
    publish.run_action(ctx,settings)
    dialog.close()


def create_dialog():
    def checkBoxChecked(dialog, value):
        dialog.set_enabled("location_var", value)
        pass

    checkbox_default = "False"
    try:
        checkbox_default = settings["checkbox"]
    except:
        pass

    path = ""
    try:
        path = settings["publish_file_location"]
    except:
        pass

    appendix = ""
    try:
        appendix = settings["publish_version_appendix"]
    except:
        pass

    dialog = ap.Dialog()
    dialog.title = "Create Referenced File"
    dialog.add_text("Copy into a dedicated Folder").add_checkbox(
        var="checkbox_var",
        callback=checkBoxChecked,
        default=(checkbox_default == "True"),
    )
    dialog.add_text("Folder\t    ").add_input(
        path,
        placeholder="published_versions",
        browse=ap.BrowseType.Folder,
        browse_path=project.path,
        var="location_var",
        enabled=False,
    )
    dialog.add_text("Appendix\t    ").add_input(
        appendix, placeholder="_published", var="appendix_var", enabled=True
    )
    dialog.add_info(
        "What should follow after the name without increment. E.g. <b>character_rig_v023.blend</b> <br>becomes <b>character_rig_published.blend</b>"
    )

    if ctx.icon:
        dialog.icon = ctx.icon

    dialog.add_button("Create File", callback=store_settings_and_run)
    dialog.show()


create_dialog()
