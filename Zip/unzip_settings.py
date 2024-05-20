import anchorpoint as ap
import apsync as aps


def store_settings(dialog):
    settings = aps.Settings()
    settings.set("delete_after_unpacking",
                 dialog.get_value("delete_after_unpacking"))
    settings.store()
    dialog.close()


def main():
    settings = aps.Settings()
    ctx = ap.Context.instance()

    delete_after_unpacking = settings.get("delete_after_unpacking", False)

    dialog = ap.Dialog()
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.title = "Unzip Settings"
    dialog.add_checkbox(text="Delete Archive after unpacking",
                        var="delete_after_unpacking", default=delete_after_unpacking)
    dialog.add_button("Apply", callback=store_settings, primary=False)
    dialog.show()


if __name__ == "__main__":
    main()
