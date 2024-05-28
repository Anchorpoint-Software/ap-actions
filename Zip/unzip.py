import anchorpoint as ap
import apsync as aps
import py7zr
import zipfile
import rarfile
import os


def unzip_file(file_path, output_dir, delete_after_unpacking):
    progress = ap.Progress("Unzipping Archive", infinite=False)
    progress.set_cancelable(True)

    try:
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as archive:
                file_list = archive.namelist()
                total_files = len(file_list)
                for index, file in enumerate(file_list):
                    if progress.canceled:
                        print("Unzipping process was canceled.")
                        progress.finish()
                        return False
                    archive.extract(file, output_dir)
                    progress.set_text(f"Unzipping {file}")
                    progress.report_progress((index + 1) / total_files)
        elif file_path.endswith('.rar'):
            with rarfile.RarFile(file_path, 'r') as archive:
                file_list = archive.namelist()
                total_files = len(file_list)
                for index, file in enumerate(file_list):
                    if progress.canceled:
                        print("Unzipping process was canceled.")
                        progress.finish()
                        return False
                    archive.extract(file, output_dir)
                    progress.set_text(f"Unzipping {file}")
                    progress.report_progress((index + 1) / total_files)
        else:
            progress.finish()
            print("Unsupported archive type.")
            return False

        progress.finish()

        # Delete the archive if the setting is enabled
        if delete_after_unpacking:
            os.remove(file_path)
            print(f"Deleted the archive: {file_path}")

        return True

    except Exception as e:
        progress.finish()
        print(f"An error occurred: {e}")
        return False


def main():
    ctx = ap.get_context()
    ui = ap.UI()

    selected_files = ctx.selected_files

    if not selected_files:
        ui.show_error("No file selected",
                      "Please select an archive file to unzip.")
        return

    archive_path = selected_files[0]
    output_dir = os.path.join(os.path.dirname(
        archive_path), os.path.splitext(os.path.basename(archive_path))[0])

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    settings = aps.Settings()
    delete_after_unpacking = settings.get("delete_after_unpacking", False)

    def unzip_and_notify():
        ui.show_info("Unpacking...",
                     f"Unpacking {os.path.basename(archive_path)}")
        success = unzip_file(archive_path, output_dir, delete_after_unpacking)
        if success:
            ui.show_success(
                "Unpacking finished", f"The archive has been unpacked to {os.path.basename(output_dir)}")

    ctx.run_async(unzip_and_notify)


if __name__ == "__main__":
    main()
