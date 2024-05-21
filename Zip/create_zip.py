import anchorpoint as ap
import apsync as aps
import zipfile
import os


class ZippingCanceledException(Exception):
    pass


def zip_files(files, base_folder, output_path, ignore_extensions, ignore_folders):
    progress = ap.Progress("Creating ZIP Archive", infinite=False)
    progress.set_cancelable(True)

    temp_output_path = f"{output_path}.part"
    archive = None

    ignore_extensions = [ext.lower() for ext in ignore_extensions]
    ignore_folders = [folder.lower() for folder in ignore_folders]

    try:
        archive = zipfile.ZipFile(temp_output_path, 'w', zipfile.ZIP_DEFLATED)
        total_files = len(files)

        for index, file in enumerate(files):
            if progress.canceled:
                raise ZippingCanceledException

            file_lower = file.lower()
            if not any(file_lower.endswith(ext) for ext in ignore_extensions) and \
               not any(ignored_folder in file_lower for ignored_folder in ignore_folders):
                relative_path = os.path.relpath(file, base_folder)
                archive.write(file, relative_path)
                # Update progress with only the filename
                progress.set_text(f"Zipping {relative_path}")
                progress.report_progress((index + 1) / total_files)

        archive.close()
        os.rename(temp_output_path, output_path)  # Rename to final output path
        progress.finish()
        return True

    except ZippingCanceledException:
        if archive is not None:
            archive.close()  # Ensure the archive is closed properly
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)  # Delete the partially created archive
        progress.finish()
        return False

    except Exception as e:
        if archive is not None:
            archive.close()  # Ensure the archive is closed properly
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)  # Delete the partially created archive
        progress.finish()
        return False


def main():
    ctx = ap.get_context()
    ui = ap.UI()

    selected_files = ctx.selected_files
    selected_folders = ctx.selected_folders

    settings = aps.Settings()
    ignore_extensions = settings.get("ignore_extensions", ["blend1"])
    ignore_folders = settings.get("ignore_folders", [])
    archive_name = settings.get("archive_name", "archive")

    if selected_files:
        output_dir = os.path.dirname(selected_files[0])
    else:
        output_dir = os.path.dirname(selected_folders[0])

    # Ensure the output directory is valid
    if not os.path.isdir(output_dir):
        output_dir = os.path.dirname(output_dir)

    output_zip = os.path.join(output_dir, f"{archive_name}.zip")

    all_files = []
    base_folder = output_dir

    for file in selected_files:
        all_files.append(file)

    for folder in selected_folders:
        for root, dirs, files in os.walk(folder):
            # Remove ignored folders from the search
            dirs[:] = [d for d in dirs if d.lower() not in ignore_folders]
            for file in files:
                full_path = os.path.join(root, file)
                all_files.append(full_path)

        if folder and base_folder not in folder:
            base_folder = os.path.commonpath([base_folder, folder])

    # Run the zipping process asynchronously
    def zip_and_notify():
        ui.show_info("Packing started...", f"Creating {archive_name}.zip")
        success = zip_files(all_files, base_folder, output_zip,
                            ignore_extensions, ignore_folders)
        if success:
            ui.show_success("Archive has been created",
                            f"Take a look at {os.path.basename(output_zip)}")

    ctx.run_async(zip_and_notify)


if __name__ == "__main__":
    main()
