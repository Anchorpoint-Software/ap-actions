# This example demonstrates how to create a simple dialog in Anchorpoint
import anchorpoint as ap
import apsync as aps
import os
import tempfile
import shutil


def get_image(workspace_id, input_path):

    # Check if a detail thumbnail already exists
    thumbnail_path = aps.get_thumbnail(input_path, True)
    if thumbnail_path:
        # Copy thumbnail to same directory with original filename
        output_dir = os.path.dirname(thumbnail_path)
        file_name = os.path.basename(input_path).split(".")[0]
        renamed_thumbnail_path = os.path.join(output_dir, file_name + ".png")

        if not os.path.exists(renamed_thumbnail_path):
            shutil.copy2(thumbnail_path, renamed_thumbnail_path)

        # trigger the copy to clipboard function
        ap.copy_files_to_clipboard([renamed_thumbnail_path])
    else:
        # get the output folder from the low res thumbnail
        output_folder = os.path.dirname(aps.get_thumbnail(input_path, False))

        if not output_folder:
            output_folder = create_temp_directory()

        # get the proper filename, rename it because the generated PNG file has a _pt appendix
        file_name = os.path.basename(input_path).split(".")[0]
        image_path = os.path.join(
            output_folder, file_name + str("_dt") + str(".png"))

        if not os.path.exists(image_path):

            # start progress
            progress = ap.Progress(
                "Copying image", "Processing", infinite=True)
            # generate the thumbnail which is a png file and put it in the temporary directory
            aps.generate_thumbnails(
                [input_path],
                output_folder,
                with_detail=True,
                with_preview=False,
                workspace_id=workspace_id,
            )
            progress.finish()

        if not os.path.exists(image_path):
            ap.UI().show_error(
                "Cannot copy to clipboard", "PNG file could not be generated"
            )
            return

        renamed_image_path = os.path.join(
            output_folder, file_name + str(".png"))

        if not os.path.exists(renamed_image_path):
            os.rename(image_path, renamed_image_path)

        # trigger the copy to clipboard function
        ap.copy_files_to_clipboard([renamed_image_path])

    ap.UI().show_success("Image copied to clipboard", "Paste it as a PNG file")


def create_temp_directory():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    return temp_dir


ctx = ap.get_context()
ctx.run_async(get_image, ctx.workspace_id, ctx.path)
