import sys
import json
import os
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
    arguments = arguments.replace("\\", "\\\\")
    msg = ""
    path = ""
    type = "cinema4d"

    # Parse the JSON string
    try:
        parsed_arguments = json.loads(arguments)
        # raise Exception("The output could not be read")
        # Access and print the "msg" object
        if "msg" in parsed_arguments:
            msg = parsed_arguments["msg"]
        if "path" in parsed_arguments:
            path = parsed_arguments["path"]
        else:
            raise Exception("The output could not be read")
    except json.JSONDecodeError:
        raise Exception("Cannot decode JSON.")

    ctx = ap.get_context()
    project_settings = aps.SharedSettings(
        ctx.project_id, ctx.workspace_id, "inc_settings")

    post_process_object = {"create_master": project_settings.get(
        "create_master_file", True)}

    publish_process = publish.publish_file(
        msg, path, type, post_process=post_process_object)
    if publish_process:
        # Print a success to stdout so the C4D plugin can read it
        sys.__stdout__.write("The file has been published")
    else:
        raise Exception("Cannot publish the file")


if __name__ == "__main__":
    sys.__stdout__.write("hallo")
    main()
