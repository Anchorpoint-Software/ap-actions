import anchorpoint as ap
import apsync as aps
import os


def store_settings(dialog):
    settings = aps.Settings()
    settings.set("ignore_extensions", dialog.get_value("ignore_extensions"))
    settings.set("ignore_folders", dialog.get_value("ignore_folders"))
    settings.set("archive_name", dialog.get_value("archive_name"))
    settings.store()
    dialog.close()


def main():
    settings = aps.Settings()
    ctx = ap.Context.instance()
    ignore_extensions = settings.get("ignore_extensions", ["blend1"])
    ignore_folders = settings.get("ignore_folders", [])
    archive_name = settings.get("archive_name", "archive")

    dialog = ap.Dialog()
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.title = "ZIP Settings"
    dialog.add_text("Ignore Files \t").add_tag_input(
        ignore_extensions, placeholder="txt", var="ignore_extensions")
    dialog.add_text("Ignore Folders \t").add_tag_input(
        ignore_folders, placeholder="temp", var="ignore_folders")
    dialog.add_text("Archive Name \t").add_input(
        archive_name, var="archive_name")
    dialog.add_button("Apply", callback=store_settings, primary=False)
    dialog.show()


if __name__ == "__main__":
    main()
