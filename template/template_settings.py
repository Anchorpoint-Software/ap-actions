import anchorpoint as ap
import apsync as aps

ctx = ap.Context.instance()
ui = ap.UI()

template_dir = ctx.inputs["template_dir"]

settings = aps.Settings("Template Settings", "workspace", ctx.yaml_dir + "/template_settings.json", user = False)

# Create a dialog container
dialog = ap.Dialog()
dialog.title = "Template Action Settings"
dialog.icon = ":/icons/settings.svg"

dialog.add_text("Templates Location")
dialog.add_input(template_dir, browse=ap.BrowseType.Folder, var="template_dir")

# Present the dialog to the user
dialog.show(settings)