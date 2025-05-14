import anchorpoint as ap
import apsync as aps
import os
import subprocess
import zipfile
import psutil

ctx = ap.get_context()
ui = ap.UI()

tag_pattern = "Editor"  # This should be configurable in the UI
max_depth = 200

def unzip_and_manage_files(zip_file_path, project_path, progress):
    if dry_run:
        print(f"Would extract from: {zip_file_path}")
        print(f"To project path: {project_path}")
        print("Would perform the following steps:")
        print("1. Delete existing files from previous sync")
        print("2. Extract all files from zip")
        print("3. Create/update extracted_binaries.txt")
        return True

    # Check if we're already at the latest state
    binary_list_path = os.path.join(project_path, "extracted_binaries.txt")
    if os.path.exists(binary_list_path):
        with open(binary_list_path, 'r') as file:
            first_line = file.readline().strip()
            current_zip = os.path.basename(zip_file_path)
            if first_line == f"Binary sync from {current_zip}":
                ui.show_info("Binaries up to date", "Editor Binaries are already at the latest state")
                progress.finish()
                return True

    # Delete existing files from previous sync if extracted_binaries.txt exists
    if os.path.exists(binary_list_path):
        with open(binary_list_path, 'r') as file:
            # Skip the header lines
            next(file)  # Skip "Binary sync from..." line
            next(file)  # Skip separator line
            for line in file:
                file_path = line.strip()
                full_path = os.path.join(project_path, file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)

    # Create a list to store unzipped files
    unzipped_files = []
    
    # Create a new progress object for extraction
    progress.finish()
    extraction_progress = ap.Progress("Extracting Binaries", "Preparing to extract files...", infinite=False)
    extraction_progress.set_cancelable(True)
    
    # Unzip the file
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # Get the total number of files to unzip
        total_files = len(zip_ref.infolist())
        extraction_progress.set_text("Extracting files...")
        
        # Extract all files, overwriting existing ones
        for index, file_info in enumerate(zip_ref.infolist()):
            # Stop process if cancel was hit by user
            if extraction_progress.canceled:
                ui.show_info("Process cancelled")
                extraction_progress.finish()
                return False
            
            zip_ref.extract(file_info, project_path)
            unzipped_files.append(file_info.filename)
            extraction_progress.report_progress((index + 1) / total_files)  # Report the progress
    
    # Write the list of unzipped files to extracted_binaries.txt
    with open(binary_list_path, 'w') as f:
        f.write(f"Binary sync from {os.path.basename(zip_file_path)}\n")
        f.write("=" * 50 + "\n")
        for file in sorted(unzipped_files):
            f.write(f"{file}\n")
    
    extraction_progress.finish()
    return True  # Indicate success

def run_setup(project_path, progress):

    # Finish the incoming progress object
    progress.finish()    
    
    try:
        # Create a single progress object for all steps
        progress = ap.Progress("Setting up Project", "Checking dependencies...", infinite=True)
        progress.set_cancelable(True)

        # Step 1: Run GitDependencies.exe
        git_dependencies_path = os.path.join(project_path, "Engine", "Binaries", "DotNET", "GitDependencies", "win-x64", "GitDependencies.exe")
        if not os.path.exists(git_dependencies_path):
            ui.show_error("Setup Error", "GitDependencies.exe not found. This is required for setting up the project.")
            progress.finish()
            return False

        # Prepare startupinfo to hide the window
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Run with --force parameter to avoid prompts
        process = subprocess.Popen(
            [
                git_dependencies_path, 
                "--force",
                "--exclude=osx64", "--exclude=osx32", "--exclude=TVOS", "--exclude=Mac", 
                "--exclude=mac-arm64", "--exclude=WinRT", "--exclude=Linux", "--exclude=Linux32", 
                "--exclude=Linux64", "--exclude=Unix", "--exclude=OpenVR", "--exclude=GoogleOboe", 
                "--exclude=GooglePlay", "--exclude=GoogleGameSDK", "--exclude=Documentation", 
                "--exclude=Samples", "--exclude=Templates", "--exclude=Android", "--exclude=HTML5", 
                "--exclude=IOS", "--exclude=GoogleVR", "--exclude=GoogleTest", "--exclude=LeapMotion",
                "--exclude=Dingo", "--exclude=Switch"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_path,
            startupinfo=startupinfo
        )
        
        # Read and print output while checking for cancellation
        while process.poll() is None:
            # Check for cancellation
            if progress.canceled:
                process.terminate()
                ui.show_info("Setup cancelled by user")
                progress.finish()
                return False
            
            # Read output
            output_line = process.stdout.readline()
            if output_line:
                # Parse progress percentage if present
                if "Updating dependencies:" in output_line:
                    try:
                        # Extract percentage from strings like "Updating dependencies: 3% (3476/90939)"
                        percent_str = output_line.split("%")[0].split(": ")[1].strip()
                        percent = float(percent_str) / 100.0  # Convert to 0-1 range
                        progress.set_text(output_line)
                        progress.report_progress(percent)
                    except (IndexError, ValueError) as e:
                        # If parsing fails, just continue
                        pass
        
        # Get final return code
        if process.returncode != 0:
            ui.show_error("GitDependencies Error", "Failed to sync dependencies")
            progress.finish()
            return False
        
        # Step 2: Setup git hooks
        git_hooks_path = os.path.join(project_path, ".git", "hooks")
        if os.path.exists(git_hooks_path):
            progress.set_text("Registering git hooks...")
            
            # Create post-checkout hook
            with open(os.path.join(git_hooks_path, "post-checkout"), 'w') as f:
                f.write("#!/bin/sh\n")
                f.write("Engine/Binaries/DotNET/GitDependencies/win-x64/GitDependencies.exe\n")
            
            # Create post-merge hook
            with open(os.path.join(git_hooks_path, "post-merge"), 'w') as f:
                f.write("#!/bin/sh\n")
                f.write("Engine/Binaries/DotNET/GitDependencies/win-x64/GitDependencies.exe\n")
            
            print("Git hooks registered successfully")
            
        # Check for cancellation
        if progress.canceled:
            ui.show_info("Setup cancelled by user")
            progress.finish()
            return False
            
        # Step 3: Install prerequisites
        prereq_path = os.path.join(project_path, "Engine", "Extras", "Redist", "en-us", "UEPrereqSetup_x64.exe")
        if os.path.exists(prereq_path):
            progress.set_text("Installing prerequisites. Make sure to accept the UAC prompt...")
            
            # Prepare special startupinfo to suppress UAC dialog as much as possible
            uac_startupinfo = None
            if os.name == 'nt':
                uac_startupinfo = subprocess.STARTUPINFO()
                uac_startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                # Use SW_HIDE to hide the window
                uac_startupinfo.wShowWindow = 0  # SW_HIDE
            
            # Run the prerequisites installer with maximum silent flags
            try:
                # Try to run with administrator privileges without showing UAC prompt
                process = subprocess.Popen(
                    [prereq_path, "/quiet", "/norestart", "/SILENT", "/SUPPRESSMSGBOXES"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=project_path,
                    startupinfo=uac_startupinfo
                )
                
                # Wait for completion with cancellation support
                while process.poll() is None:
                    if progress.canceled:
                        process.terminate()
                        ui.show_info("Setup cancelled by user")
                        progress.finish()
                        return False
                
                print("Prerequisites installed successfully")
            
            except Exception as e:
                print(f"Warning: Prerequisites installation encountered an issue: {str(e)}")
                print("Continuing with next steps...")
                # Continue anyway as this may not be critical
            
        # Check for cancellation
        if progress.canceled:
            ui.show_info("Setup cancelled by user")
            progress.finish()
            return False
            
        # Step 4: Register engine installation
        version_selector_path = os.path.join(project_path, "Engine", "Binaries", "Win64", "UnrealVersionSelector-Win64-Shipping.exe")
        if os.path.exists(version_selector_path):
            progress.set_text("Registering engine installation...")
            
            # Register the engine
            process = subprocess.Popen(
                [version_selector_path, "/register", "/unattended"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=project_path,
                startupinfo=startupinfo
            )
            
            # Wait for completion with cancellation support
            while process.poll() is None:
                if progress.canceled:
                    process.terminate()
                    ui.show_info("Setup cancelled by user")
                    progress.finish()
                    return False
            
            print("Engine registered successfully")
            
        progress.set_text("Setup completed successfully")
        progress.finish()
        return True
        
    except Exception as e:
        ui.show_error("Setup Error", str(e))
        return False

def is_unreal_running(project_path):
    if dry_run:
        print(f"Would check if Unreal Editor is running in: {project_path}")
        return False

    unreal_exe = os.path.join(project_path, "Engine", "Binaries", "Win64", "UnrealEditor.exe")
    
    # Get the absolute path to handle any case differences
    unreal_exe = os.path.abspath(unreal_exe)
    
    # Check all running processes
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            # Get process info
            proc_info = proc.info
            if proc_info['exe']:
                # Compare the absolute paths
                if os.path.abspath(proc_info['exe']) == unreal_exe:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def find_uproject_files(project_path):
    
    uproject_files = []
    depth = 3
    
    # Get all directories at the specified depth (currently set to depth levels)
    for root, dirs, files in os.walk(project_path, topdown=True):
        # Skip Engine and Templates folders
        if 'Engine' in dirs:
            dirs.remove('Engine')
        if 'Templates' in dirs:
            dirs.remove('Templates')
            
        # Only process up to depth levels deep
        rel_path = os.path.relpath(root, project_path)
        if rel_path == '.' or rel_path.count(os.sep) <= depth:
            # Look for .uproject files in current directory
            for file in files:
                if file.endswith('.uproject'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, project_path)
                    uproject_files.append(rel_path)
        
        # Stop walking deeper than depth levels
        if rel_path.count(os.sep) >= depth:
            dirs.clear()
    
    return uproject_files

def get_commit_history(project_path):
    commit_history = []
    try:
        startupinfo = None
        if os.name == 'nt':  # Check if the OS is Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Get current commit ID
        current_commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=project_path,
            text=True,
            startupinfo=startupinfo
        ).strip()

        if dry_run:
            print(f"Current commit: {current_commit}")
            print(f"Searching for tag pattern: '{tag_pattern}'")
            print(f"Maximum depth: {max_depth} commits")

        # Get commit history with tags
        commit_history = subprocess.check_output(
            ['git', 'log', '--pretty=format:%H %d', f'-{max_depth}'],
            cwd=project_path,
            text=True,
            startupinfo=startupinfo
        ).splitlines()

        if dry_run:
            print(f"Found {len(commit_history)} commits to check\n")
            
    except subprocess.CalledProcessError as e:
        ui.show_error("Git Error", f"Failed to retrieve commit information: {str(e)}")
        return None
    return commit_history

def get_matching_commit_id(commit_history,tag_pattern):
    if not commit_history:
        if dry_run:
            print("\nNo commits found in history")
        ui.show_error("No commits found", "Failed to retrieve commit history")
        return None, None

    # Process commits starting from current
    for commit_line in commit_history:
        parts = commit_line.split()
        commit_id = parts[0]
        tags = [tag.strip('()') for tag in parts[1:]] if len(parts) > 1 else []
        
        if dry_run:
            print(f"\nChecking commit: {commit_id}")
            if tags:
                print(f"Tags: {', '.join(tags)}")
            else:
                print("No tags found")
        
        # Check if any tag matches our pattern
        matching_tag = next((tag for tag in tags if tag_pattern in tag), None)
        
        if matching_tag:
            if dry_run:
                print(f"Found matching tag: {matching_tag}")
            return commit_id, matching_tag
    
    # If no matching tag was found
    if dry_run:
        print("\nNo matching binaries found in the search")
    ui.show_error("No compatible tag found", f"No tag found for commits with tag pattern '{tag_pattern}'")
    return None, None

def launch_editor(project_path,launch_project_path):
    if not os.path.isabs(launch_project_path):
        # Append the relative path to the project_path to get the absolute path
        launch_project_path = os.path.join(project_path, launch_project_path)

    if dry_run:
        print(f"Launch project path {launch_project_path}")
    
    if os.path.exists(launch_project_path):
        try:
            # Use shell=False with a list argument
            subprocess.Popen([launch_project_path], shell=True)
            ui.show_success("Binaries synced", f"Launching project {os.path.basename(launch_project_path)}")
        except Exception as e:
            ui.show_info("Binaries synced", f"Failed to launch project: {str(e)}")
    
def run_sync_processes(sync_dependencies,source_path,launch_project_path,tag_pattern):

    # Start the progress 
    progress = ap.Progress("Syncing Editor","Initializing...", infinite=True)
    progress.set_cancelable(True)

    # Get project path before closing dialog
    project_path = ctx.project_path
    
    # Check if Unreal Editor is running
    if is_unreal_running(project_path):
        ui.show_info("Unreal Editor is running", "Please close Unreal Engine before proceeding with the binary sync.")
        return
    
    commit_history = get_commit_history(project_path)
    if commit_history is None:
        return
        
    matching_commit_id, matching_tag = get_matching_commit_id(commit_history,tag_pattern)
    if matching_commit_id is None:
        return
        
    # Found a matching tag, check for zip file
    zip_file_name = f"{matching_commit_id}.zip"
    zip_file_path = os.path.join(source_path, zip_file_name)
    
    if os.path.exists(zip_file_path):
        if dry_run:
            print(f"Found matching zip file: {zip_file_path}")
            print("\nWould perform the following actions:")
            print(f"1. {'Run setup script' if sync_dependencies else 'Skip setup script'}")
            print(f"2. Extract binaries from {matching_tag}")
            if launch_project_path:
                print(f"3. Launch project: {launch_project_path}")
            progress.finish()
            return
        
        # Run the setup script if enabled
        if sync_dependencies:
            if not run_setup(project_path, progress):
                return
        
        try:
            if not unzip_and_manage_files(zip_file_path, project_path, progress):
                return  # If extraction was canceled or failed
            
            # Launch the selected uproject file if one was selected
            if launch_project_path:
                launch_editor(project_path,launch_project_path)
            else:
                ui.show_success("Binaries synced", f"Files extracted from {matching_tag.replace(",","")}")
            return
            
        except Exception as e:
            ui.show_error("Extraction failed", str(e))
            return
        
    elif dry_run:
        print(f"Zip file not found: {zip_file_path}")
    else:
        ui.show_error("No compatible Zip file", f"No binaries found for tag '{matching_tag.replace(",","")}'")
    
def initialize():
    global dry_run
    
    project_path = ctx.project_path
    project_id = ctx.project_id
    workspace_id = ctx.workspace_id
    uproject_files = find_uproject_files(project_path)      

    # Get the project settings
    local_settings = aps.Settings()  
    
    # Check for .uedependencies file
    uedependencies_path = os.path.join(project_path, ".uedependencies")
    if os.path.exists(uedependencies_path):
        sync_dependencies = local_settings.get(project_path+"_sync_dependencies", False)
    else:
        sync_dependencies = True
        
    dry_run = local_settings.get(project_path+"_dry_run", False)    
    binary_source = local_settings.get(project_path+"_binary_source", "")

    shared_settings = aps.SharedSettings(project_id,workspace_id,"unreal")
    tag_pattern = shared_settings.get("_tag_pattern", "") 

    if dry_run:
        ui.show_console()

    if not tag_pattern:
        if dry_run:
            print("Tag pattern is empty. Use something like <<Editor>> for all Git tags named <<Editor-1>>, <<Editor-2>>, etc.")
        ui.show_error("No tag has been set", "Please define a tag pattern in the project settings")
        return

    # Terminate if it's not an Unreal Project
    if not uproject_files:
        if dry_run:
            print("Could not find any .uproject file")
        ui.show_error("Not an Unreal project", "Check your project folder")
        return
    
    launch_project_display_name = local_settings.get(project_path+"_launch_project_display_name", uproject_files[0])    

    # Terminate when there is no source for the zip file defined in the project settings
    if not binary_source:
        ui.show_error("No ZIP Location defined", "Please set up a location in the project settings")
        return
    
    launch_project_path = "" 
    for uproject_file in uproject_files:
        if launch_project_display_name in uproject_file:
            launch_project_path = uproject_file
            break

    ctx.run_async(run_sync_processes,sync_dependencies,binary_source,launch_project_path,tag_pattern)   

if __name__ == "__main__":
    initialize()