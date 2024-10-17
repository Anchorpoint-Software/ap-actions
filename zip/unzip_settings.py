import anchorpoint as ap
import apsync as aps
import unzip

def store_settings(dialog, _):
    settings = aps.Settings()
    settings.set("delete_after_unpacking",
                 dialog.get_value("delete_after_unpacking"))
    settings.store()

def button_clicked(dialog):
    dialog.close()
    unzip.run_action()

def main():
    settings = aps.Settings()
    ctx = ap.Context.instance()
    delete_after_unpacking = settings.get("delete_after_unpacking", False)

    dialog = ap.Dialog()
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.title = "Unzip Settings"
    dialog.add_checkbox(
        text="Delete Archive after unpacking", var="delete_after_unpacking", default=delete_after_unpacking, callback=store_settings)
    dialog.add_button("Unzip", callback=button_clicked)
    dialog.show()


if __name__ == "__main__":
    main()
