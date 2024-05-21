import anchorpoint as ap
import apsync as aps
import os


def store_settings(dialog, _):
    settings = aps.Settings()
    settings.set("ignore_extensions", dialog.get_value("ignore_extensions"))
    settings.set("ignore_folders", dialog.get_value("ignore_folders"))
    settings.set("archive_name", dialog.get_value("archive_name"))
    settings.set("exclude_incremental_saves",
                 dialog.get_value("exclude_incremental_saves"))
    settings.store()


def main():
    settings = aps.Settings()
    ctx = ap.Context.instance()
    ignore_extensions = settings.get("ignore_extensions", ["blend1"])
    ignore_folders = settings.get("ignore_folders", [])
    archive_name = settings.get("archive_name", "archive")
    exclude_incremental_saves = settings.get(
        "exclude_incremental_saves", False)

    dialog = ap.Dialog()
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.title = "ZIP Settings"
    dialog.add_text("Ignore Files \t").add_tag_input(
        ignore_extensions, placeholder="txt", var="ignore_extensions", callback=store_settings)
    dialog.add_text("Ignore Folders \t").add_tag_input(
        ignore_folders, placeholder="temp", var="ignore_folders", callback=store_settings)
    dialog.add_text("Archive Name \t").add_input(
        archive_name, var="archive_name", callback=store_settings, width=300, placeholder="archive")
    dialog.add_switch(
        text="Exclude old incremental saves", var="exclude_incremental_saves", default=exclude_incremental_saves, callback=store_settings)
    dialog.add_info(
        "Adds only the latest version, e.g. asset_v023.blend, to the archive and <br>ignores incremental saves below it")
    dialog.show()


if __name__ == "__main__":
    main()
