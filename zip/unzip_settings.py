import anchorpoint as ap
import apsync as aps


def store_settings(dialog, _):
    settings = aps.Settings()
    settings.set("delete_after_unpacking",
                 dialog.get_value("delete_after_unpacking"))
    settings.store()


def main():
    settings = aps.Settings()
    ctx = ap.Context.instance()
    delete_after_unpacking = settings.get("delete_after_unpacking", False)

    dialog = ap.Dialog()
    if ctx.icon:
        dialog.icon = ctx.icon
    dialog.title = "Unzip Settings"
    dialog.add_switch(
        text="Delete Archive after unpacking", var="delete_after_unpacking", default=delete_after_unpacking, callback=store_settings)
    dialog.show()


if __name__ == "__main__":
    main()
