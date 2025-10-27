import sys
import json
import apsync as aps
import anchorpoint as ap
import publish

# Summary
# This script is called by the Anchorpoint plugin for Cinema 4D to publish a file.
# It takes a look at the file path and the message provided by the the cinema 4D plugin and initiates the publish process.

# This function is called form the C4D plugin


def main():
    # add the parent directory to the sys.path to be able to import inc_publish_utils

    arguments = sys.argv[1]
    msg = ""
    doc_path = ""
    additional_file_objects = []
    thumbnail_path = ""

    # Parse the JSON string
    try:
        parsed_arguments = json.loads(arguments)
        # Access and print the "msg" object
        if "msg" in parsed_arguments:
            msg = parsed_arguments["msg"]
        if "doc-path" in parsed_arguments:
            doc_path = parsed_arguments["doc-path"]
        if "screenshot" in parsed_arguments:
            thumbnail_path = parsed_arguments["screenshot"]
    except json.JSONDecodeError:
        raise Exception("Cannot decode JSON.")

    # check if post processing needs to be done
    ctx = ap.get_context()
    project_settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings"
    )
    data_object = {
        "create_master": project_settings.get("create_master_file", True),
        "attached_doc_thumbnail": thumbnail_path,
        "additional_file_objects": additional_file_objects,
    }

    # Trigger the publish process
    try:
        publish_successful = publish.publish_file(
            msg, doc_path, data_object=data_object)
        # Print a success to stdout so the C4D plugin can read it
        if publish_successful:
            sys.__stdout__.write("The file has been published")
            ap.log_success("DCC publish successful")
    except Exception as e:
        sys.__stdout__.write("An issue has occurred: " + str(e))
        ap.log_error("DCC publish failed")


if __name__ == "__main__":
    main()
