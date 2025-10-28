import anchorpoint as ap
import apsync as aps
import os

ctx = ap.get_context()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "unreal_binary_sync")

# keys are stored as settings and values are displayed in the dropdown

BINARY_LOCATIONS = {
    "folder": "Shared Folder",
    "s3": "S3 Cloud Storage"
}


def apply_callback(dialog, value):
    # Get the selected value from the dropdown
    binary_location_value = dialog.get_value("binary_location_type_var")

    settings.set("tag_pattern", dialog.get_value("tag_pattern_var"))

    if (binary_location_value == "S3 Cloud Storage"):
        settings.set("binary_location_type", "s3")

        dialog.set_enabled("access_key_var", True)
        dialog.set_enabled("secret_key_var", True)
        dialog.set_enabled("endpoint_url_var", True)
        dialog.set_enabled("bucket_name_var", True)
        settings.set("access_key", dialog.get_value("access_key_var"))
        settings.set("secret_key", dialog.get_value("secret_key_var"))
        settings.set("endpoint_url", dialog.get_value("endpoint_url_var"))
        settings.set("bucket_name", dialog.get_value("bucket_name_var"))
    else:
        settings.set("binary_location_type", "folder")

        dialog.set_enabled("access_key_var", False)
        dialog.set_enabled("secret_key_var", False)
        dialog.set_enabled("endpoint_url_var", False)
        dialog.set_enabled("bucket_name_var", False)

    settings.store()


def main():
    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "Sync Settings"

    binary_location = settings.get("binary_location_type", "folder")
    tag_pattern = settings.get("tag_pattern", "")
    access_key = settings.get("access_key", "")
    secret_key = settings.get("secret_key", "")
    endpoint_url = settings.get("endpoint_url", "")
    bucket_name = settings.get("bucket_name", "")

    dialog.add_text("Tag Pattern", width=110).add_input(
        placeholder="Editor",
        var="tag_pattern_var",
        default=tag_pattern,
        callback=apply_callback
    )
    dialog.add_info("Specify a pattern for Git tags that tells Anchorpoint that there is a binary attached to a<br>commit. E.g. use <b>Editor</b> if your tagis named <b>Editor-1</b>. Learn more about <a href='https://docs.anchorpoint.app/docs/version-control/features/binary-sync/'>binary syncing</a>.")

    dialog.add_text("Binary Location", width=110).add_dropdown(
        default=BINARY_LOCATIONS[binary_location],
        values=list(BINARY_LOCATIONS.values()),
        var="binary_location_type_var",
        callback=apply_callback
    )
    dialog.add_info("Select where the binaries are stored in your studio. A shared folder can be something<br>like a Google Drive. An S3 Cloud Storage can be something like AWS S3 or Backblaze B2.")

    dialog.start_section("S3 Access Credentials", foldable=True)
    dialog.add_info(
        "Only applicable when using S3 Cloud Storage. Provide the access credentials to access<br>your S3 bucket where the binaries are stored.")
    dialog.add_text("Access Key", width=110).add_input(
        default=access_key,
        placeholder="7879ABCD1234EFGH...",
        var="access_key_var", enabled=(binary_location == "s3"),
        callback=apply_callback
    )
    dialog.add_text("Secret Key", width=110).add_input(
        default=secret_key,
        placeholder="s9d8f7987s9d8f7987s9d8f7987...",
        var="secret_key_var",
        enabled=(binary_location == "s3"),
        callback=apply_callback
    )
    dialog.add_text("Endpoint URL", width=110).add_input(
        default=endpoint_url,
        placeholder="s3.some-cloud-provider.com...",
        var="endpoint_url_var", enabled=(binary_location == "s3"),
        callback=apply_callback
    )
    dialog.add_text("Bucket Name", width=110).add_input(
        default=bucket_name,
        placeholder="my_bucket/unreal_binaries...",
        var="bucket_name_var", enabled=(binary_location == "s3"),
        callback=apply_callback
    )
    dialog.end_section()

    # Present the dialog to the user
    dialog.show()


main()
