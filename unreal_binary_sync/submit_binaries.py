import subprocess
import sys
import os
import tempfile
import zipfile
import anchorpoint as ap
import apsync as aps
from pathlib import Path
from datetime import datetime
import re


def compile_binaries(engine_dir, project_dir, project_name, editor_target):
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
        for line in process.stdout:
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


def add_incremental_git_tag(project_dir, tag_pattern):
    tag_prefix = tag_pattern+"-"
    highest_number = 0

    try:
        # Get all tags and their commit hashes
        result = subprocess.run(
            ['git', 'tag', '--list', f'{tag_prefix}*'],
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

        # If no tags found, start with 1
        if highest_number == 0:
            new_tag = f"{tag_prefix}1"
        else:
            new_tag = f"{tag_prefix}{highest_number + 1}"

        # Tag the latest commit
        subprocess.run(
            ['git', 'tag', new_tag],
            cwd=project_dir,
            check=True
        )
        print(f"Added new git tag: {new_tag}")

    except subprocess.CalledProcessError as e:
        print(f"Error adding git tag: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)


def get_git_commit_id(project_dir):
    try:
        # Run git command to get the full commit hash
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
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


def create_binaries_zip(project_dir, output_dir):
    """
    Create a ZIP file of the project's Binaries folder and save it to the desktop.

    Args:
        project_dir (Path): Path to the project directory
        project_name (str): Name of the project
    """
    binaries_dir = project_dir / "Binaries"
    plugins_dir = project_dir / "Plugins"

    # Check if main Binaries folder exists
    if not binaries_dir.exists():
        print(f"Warning: Main Binaries folder not found at {binaries_dir}")

    # Find plugin binaries
    plugin_binaries = []
    if plugins_dir.exists():
        for plugin_path in plugins_dir.iterdir():
            if plugin_path.is_dir():
                plugin_binaries_dir = plugin_path / "Binaries"
                if plugin_binaries_dir.exists():
                    plugin_binaries.append(plugin_binaries_dir)
                    print(f"Found plugin binaries: {plugin_binaries_dir}")

    # Check if we have any binaries to zip
    all_binary_dirs = []
    if binaries_dir.exists():
        all_binary_dirs.append(binaries_dir)
    all_binary_dirs.extend(plugin_binaries)

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
    print(
        f"Main binaries: {binaries_dir if binaries_dir.exists() else 'Not found'}")
    if plugin_binaries:
        print(f"Plugin binaries: {len(plugin_binaries)} plugin(s)")
    print(f"Destination: {zip_path}")

    # Files to exclude from the ZIP
    excluded_extensions = {'.pdb', '.exp'}

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all binary directories and add all files
            for binary_dir in all_binary_dirs:
                print(f"Processing directory: {binary_dir}")
                for file_path in binary_dir.rglob('*'):
                    if file_path.is_file():
                        # Skip files with excluded extensions
                        if file_path.suffix.lower() in excluded_extensions:
                            continue

                        # Calculate relative path for the archive
                        arc_name = file_path.relative_to(project_dir)
                        zipf.write(file_path, arc_name)
                        print(f"Added: {arc_name}")

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


def upload_to_s3(zip_file_path):
    ui = ap.UI()
    ctx = ap.get_context()
    try:
        import boto3
    except ImportError:
        ctx.install("boto3")
        import boto3

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
        with open(zip_file_path, "rb") as f:
            s3_client.upload_fileobj(f, bucket_name, zip_file_name)
        print(f"Successfully uploaded {zip_file_name} to S3.")
        return True
    except Exception as e:
        print(
            f"Failed to upload to S3: {str(e)}", file=sys.stderr)
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


def submit_binaries_async(engine_dir, project_dir, project_name, editor_target, output_dir, tag_pattern):
    ui = ap.UI()
    ctx = ap.get_context()
    shared_settings = aps.SharedSettings(
        ctx.workspace_id, "unreal_binary_sync")

    binary_location = shared_settings.get(
        "binary_location_type", "folder")
    # Use Unreal Build Tool to compile the binaries, skipping if already built
    compile_binaries(engine_dir, project_dir, project_name, editor_target)
    # Create the zip file
    zip_file_path = create_binaries_zip(project_dir, output_dir)

    if binary_location == "s3":
        s3_upload = upload_to_s3(zip_file_path)
        if not s3_upload:
            ui.show_error("S3 Upload Failed",
                          "The binaries could not be uploaded to S3. Check the console for more information.")
            return
        # Delete the temp zip after upload
        delete_temp_zip(zip_file_path)

    add_incremental_git_tag(project_dir, tag_pattern)
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
    ctx.run_async(submit_binaries_async, engine_dir,
                  project_dir, project_name, editor_target, output_dir, tag_pattern)


if __name__ == "__main__":
    main()
