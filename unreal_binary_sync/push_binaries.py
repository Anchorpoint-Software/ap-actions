import subprocess
import sys
import os
import tempfile
import zipfile
import anchorpoint as ap
import apsync as aps
from pathlib import Path
import re
import platform


def compile_binaries(engine_dir, project_dir, project_name, editor_target, progress):
    ui = ap.UI()

    print(
        f"Compiling Binaries for project {project_name} at {project_dir}, using Engine at {engine_dir}")

    # Path to UnrealBuildTool
    unreal_build_tool = engine_dir / "Engine" / "Binaries" / \
        "DotNET" / "UnrealBuildTool" / "UnrealBuildTool.exe"

    # Path to project file
    project_file = project_dir / f"{project_name}.uproject"

    # Verify paths exist
    if not unreal_build_tool.exists():
        print(
            f"Error: UnrealBuildTool not found at {unreal_build_tool}", file=sys.stderr)
        ui.show_error("UnrealBuildTool not found",
                      "Check the console for more information")
        sys.exit(1)

    if not project_file.exists():
        print(
            f"Error: Project file not found at {project_file}", file=sys.stderr)
        ui.show_error("Project file not found",
                      "Check the console for more information")
        sys.exit(1)

    # Build the command
    cmd = [
        str(unreal_build_tool),
        "Development",
        "Win64",
        editor_target,
        f"-project={project_file}",
        "-useprecompiled"
    ]
    progress.set_text("Compiling, see console for details...")

    try:
        # Execute the command and stream output line by line to the current console
        # Hide the window on Windows by setting creationflags
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags
        )
        # Stream each non-empty line to the console
        for line in process.stdout:  # pyright: ignore[reportOptionalIterable]
            if line.strip():  # Only print non-empty lines
                print(line)
        process.wait()
        if process.returncode == 0:
            print(
                f"Build completed successfully with exit code {process.returncode}")
        else:
            raise subprocess.CalledProcessError(process.returncode, cmd)

    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}", file=sys.stderr)
        ui.show_error("Cannot create the build",
                      "Check the console for more information")
        sys.exit(e.returncode)

    except FileNotFoundError:
        print(f"Error: Could not execute {unreal_build_tool}", file=sys.stderr)
        ui.show_error("UnrealBuildTool not found",
                      "Check the console for more information")
        sys.exit(1)


def get_git_executable():
    application_dir = ap.get_application_dir()
    git_path = None
    if platform.system() == "Windows":
        git_path = os.path.join(application_dir, "plugins", "git")
        git_exe = os.path.join(git_path, "cmd", "git.exe")
    elif platform.system() == "Darwin":
        git_path = os.path.join(application_dir, "..", "Resources", "git")
        git_exe = os.path.join(git_path, "bin", "git")
    else:
        raise RuntimeError("Unsupported Platform")

    if (git_path):
        return os.path.normpath(git_exe)
    else:
        return "git"  # Fallback to system git that is installed on the system


def add_incremental_git_tag(project_dir, tag_pattern):
    tag_prefix = tag_pattern+"-"
    highest_number = 0

    # Use bundled git instead of system git
    git_exe = get_git_executable()

    try:
        # Get all tags and their commit hashes
        result = subprocess.run(
            [git_exe, 'tag', '--list', f'{tag_prefix}*'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.strip().splitlines()

        # Find highest Game-NUMBER tag
        for tag in tags:
            match = re.match(rf"{tag_prefix}(\d+)$", tag)
            if match:
                num = int(match.group(1))
                if num > highest_number:
                    highest_number = num

        # Get the latest commit hash
        result_commit = subprocess.run(
            [git_exe, 'rev-parse', 'HEAD'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        latest_commit = result_commit.stdout.strip()

        # Get tags pointing to the latest commit
        result_tags_on_commit = subprocess.run(
            [git_exe, 'tag', '--points-at', latest_commit],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        tags_on_commit = result_tags_on_commit.stdout.strip().splitlines()

        # If the latest commit already has a tag, skip tagging
        if tags_on_commit:
            print(
                f"Latest commit already has tag(s): {tags_on_commit}. Skipping tag creation.")
            return

        # If no tags found, start with 1
        if highest_number == 0:
            new_tag = f"{tag_prefix}1"
        else:
            new_tag = f"{tag_prefix}{highest_number + 1}"

        # Tag the latest commit
        subprocess.run(
            [git_exe, 'tag', new_tag],
            cwd=project_dir,
            check=True
        )
        print(f"Added new git tag: {new_tag}")

        # Push the tag to the remote repository
        subprocess.run(
            [git_exe, 'push', 'origin', new_tag],
            cwd=project_dir,
            check=True
        )
        print(f"Pushed tag {new_tag} to remote repository")

    except subprocess.CalledProcessError as e:
        print(f"Error adding git tag: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)


def get_git_commit_id(project_dir):
    # Use bundled git instead of system git
    git_exe = get_git_executable()

    try:
        # Run git command to get the full commit hash
        result = subprocess.run(
            [git_exe, 'rev-parse', 'HEAD'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        commit_id = result.stdout.strip()
        print(f"Latest commit ID: {commit_id}")
        return commit_id
    except subprocess.CalledProcessError:
        print(
            "Warning: Could not get git commit ID (not a git repository or git not found)")
        return 'unknown'
    except FileNotFoundError:
        print("Warning: Git not found in PATH")
        return 'unknown'


def find_uproject_file(project_path):
    project_path = Path(project_path)

    # First, check if there's a .uproject file directly in the given path
    for file in project_path.glob('*.uproject'):
        print(f"Found .uproject file: {file}")
        return file

    # If not found in the root, search all subfolders recursively
    print(
        f"No .uproject file found in {project_path}, searching subfolders...")
    for file in project_path.rglob('*.uproject'):
        print(f"Found .uproject file in subfolder: {file}")
        return file

    # If still not found, return None
    print(f"No .uproject file found in {project_path} or its subfolders")
    return None


def find_all_binaries_dirs(project_dir):
    """
    Recursively find all folders named "Binaries" within the project directory.
    Skips folders named "Content", "Intermediate", "Saved", "DerivedDataCache", "Source", and "Config".

    Args:
        project_dir (Path): Path to the project directory

    Returns:
        list: List of Path objects pointing to Binaries directories
    """
    all_binary_dirs = []
    excluded_folders = {"Content", "Intermediate",
                        "Saved", "DerivedDataCache", "Source", "Config"}

    # Recursively search for all "Binaries" folders
    for binaries_dir in project_dir.rglob("Binaries"):
        if binaries_dir.is_dir():
            # Check if any parent directory is in the excluded list
            if not any(part in excluded_folders for part in binaries_dir.parts):
                all_binary_dirs.append(binaries_dir)
                print(f"Found binaries: {binaries_dir}")
            else:
                print(f"Skipping binaries in excluded folder: {binaries_dir}")

    return all_binary_dirs


def create_binaries_zip(project_dir, output_dir, progress, max_progress):
    """
    Create a ZIP file of the project's Binaries folder and save it to the desktop.

    Args:
        project_dir (Path): Path to the project directory
        project_name (str): Name of the project
    """

    progress.set_text(f"Searching for Binaries folders...")
    # Find all Binaries directories
    all_binary_dirs = find_all_binaries_dirs(project_dir)

    if not all_binary_dirs:
        print("Warning: No binaries found to zip")
        return

    # Get commit ID for filename
    commit_id = get_git_commit_id(project_dir)
    zip_filename = f"{commit_id}.zip"
    zip_path = os.path.join(output_dir, zip_filename)

    # Check if file exists and inform about overwrite
    if os.path.exists(zip_path):
        print(f"File already exists and will be overwritten: {zip_path}")
    else:
        print(f"Creating new ZIP file: {zip_path}")

    print("------ Creating ZIP archive of Binaries folders ------")
    print(f"Found {len(all_binary_dirs)} Binaries folder(s)")
    print(f"Destination: {zip_path}")

    # Files to exclude from the ZIP
    excluded_extensions = {'.pdb', '.exp'}

    # Gather all files to be zipped and count them
    files_to_zip = []
    for binary_dir in all_binary_dirs:
        for file_path in binary_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() not in excluded_extensions:
                files_to_zip.append(file_path)
    total_files = len(files_to_zip)
    print(f"Total files to zip: {total_files}")
    progress.set_text(f"Zipping {total_files} files...")

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for idx, file_path in enumerate(files_to_zip, 1):
                arc_name = file_path.relative_to(project_dir)
                zipf.write(file_path, arc_name)
                print(f"Added: {arc_name}")
                progress.report_progress(idx / total_files * max_progress)
        print(f"Successfully created ZIP archive: {zip_path}")
        return zip_path

    except Exception as e:
        print(f"Error creating ZIP archive: {e}", file=sys.stderr)


def get_s3_credentials():
    ctx = ap.get_context()
    shared_settings = aps.SharedSettings(
        ctx.workspace_id, "unreal_binary_sync")

    access_key = shared_settings.get("access_key", "")
    secret_key = shared_settings.get("secret_key", "")
    endpoint_url = shared_settings.get("endpoint_url", "")
    bucket_name = shared_settings.get("bucket_name", "")
    if not all([access_key, secret_key, endpoint_url, bucket_name]):
        return False
    return access_key, secret_key, endpoint_url, bucket_name


def upload_to_s3(zip_file_path, progress):
    ui = ap.UI()
    ctx = ap.get_context()
    try:
        import boto3  # pyright: ignore[reportMissingImports]
    except ImportError:
        ctx.install("boto3")
        import boto3  # pyright: ignore[reportMissingImports]

    creds = get_s3_credentials()
    if not creds:
        ui.show_error("S3 Credentials Missing",
                      "Please check your S3 settings in the action configuration.")
        return False
    access_key, secret_key, endpoint_url, bucket_name = creds

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url
    )

    zip_file_name = os.path.basename(zip_file_path)
    try:
        print(f"Uploading {zip_file_name} to S3 bucket {bucket_name}...")
        file_size = os.path.getsize(zip_file_path)
        uploaded = 0
        chunk_size = 1024 * 1024  # 1 MB

        with open(zip_file_path, "rb") as f:
            # Create a callback for progress tracking
            def upload_callback(bytes_uploaded):
                nonlocal uploaded
                uploaded += bytes_uploaded
                percent = min(uploaded / file_size, 1.0)
                progress.report_progress(
                    0.6 + percent * 0.4)  # Scale to 60-100%
                if progress.canceled:
                    raise Exception("Upload cancelled by user")

            s3_client.upload_fileobj(
                f, bucket_name, zip_file_name,
                Callback=upload_callback
            )
        print(f"Successfully uploaded {zip_file_name} to S3.")
        return True
    except Exception as e:
        print(
            f"Failed to upload to S3: {str(e)}")
        ui.show_error("S3 Upload Issue",
                      "Check your S3 settings and permissions.")
        return False


def delete_temp_zip(local_zip_file_path):
    try:
        if os.path.exists(local_zip_file_path):
            os.remove(local_zip_file_path)
            print(f"Deleted temp zip: {local_zip_file_path}")
    except Exception as e:
        print(f"Failed to delete temp zip: {str(e)}")


def push_binaries_async(engine_dir, project_dir, project_name, editor_target, output_dir, tag_pattern):
    ui = ap.UI()
    ctx = ap.get_context()
    progress = ap.Progress("Submitting Binaries",
                           "Compiling...", infinite=True)
    progress.set_cancelable(True)
    shared_settings = aps.SharedSettings(
        ctx.workspace_id, "unreal_binary_sync")

    binary_location = shared_settings.get(
        "binary_location_type", "folder")
    # Use Unreal Build Tool to compile the binaries, skipping if already built
    compile_binaries(engine_dir, project_dir,
                     project_name, editor_target, progress)
    # Create the zip file
    if binary_location == "s3":
        zip_file_path = create_binaries_zip(
            project_dir, output_dir, progress, 0.6)
    else:
        zip_file_path = create_binaries_zip(
            project_dir, output_dir, progress, 1.0)

    if binary_location == "s3":
        s3_upload = upload_to_s3(zip_file_path, progress)
        if not s3_upload:
            ui.show_error("S3 Upload Failed",
                          "The binaries could not be uploaded to S3. Check the console for more information.")
            progress.finish()
            return
        # Delete the temp zip after upload
        delete_temp_zip(zip_file_path)

    add_incremental_git_tag(project_dir, tag_pattern)
    progress.finish()
    ui.show_success("Binaries Submitted")


def main():
    ctx = ap.get_context()
    ui = ap.UI()
    shared_settings = aps.SharedSettings(
        ctx.workspace_id, "unreal_binary_sync")

    binary_location = shared_settings.get(
        "binary_location_type", "folder")
    tag_pattern = shared_settings.get("tag_pattern", "")
    if tag_pattern == "":
        ui.show_error("Tag Pattern Not Set",
                      "Please set the Tag Pattern in the package settings.")
        return
    local_settings = aps.Settings()

    # Hardcoded variables - modify these as needed
    # Path to Unreal Engine installation
    engine_dir = local_settings.get(
        ctx.project_path+"_engine_directory", "")
    if not engine_dir:
        ui.show_error("Engine Directory Not Set",
                      "Please set the Engine Directory in the project settings.")
        return
    engine_dir = Path(engine_dir)
    print(f"Using Engine Directory: {engine_dir}")
    # Path to your project directory
    project_file = find_uproject_file(ctx.project_path)
    if not project_file:
        ui.show_error("No .uproject file found in the specified project path.")
        return

    project_dir = project_file.parent
    project_name = os.path.basename(project_file.stem)  # Name of your project
    # Editor target to build, currently hardcoded
    editor_target = f"{project_name}Editor"
    # Get desktop path
    output_dir = ""
    if binary_location == "folder":
        output_dir = local_settings.get(
            ctx.project_path+"_binary_source", "")
        if not output_dir:
            ui.show_error("Binary Source Not Set",
                          "Please set the Binary Source folder in the project settings.")
            return
        output_dir = Path(output_dir)
        print(f"Using output directory from local settings: {output_dir}")
    else:
        # Use a temp directory for S3 uploads
        output_dir = tempfile.gettempdir()
        print(f"Using temporary output directory for S3 upload: {output_dir}")

    ui.show_console()
    ctx.run_async(push_binaries_async, engine_dir,
                  project_dir, project_name, editor_target, output_dir, tag_pattern)


if __name__ == "__main__":
    main()
