# Unreal Binary Sync

A comprehensive solution for syncing compiled Unreal Engine binaries across development teams using Anchorpoint (Git) similar to Unreal Game Sync for Perforce. This system allows teams to share pre-compiled binaries instead of requiring everyone to build from source. This system works for game binaries when using the Unreal Editor from the Epic Games Launcher and when you build the Editor from source. You can find more information on how to use it in our [documentation](https://docs.anchorpoint.app/docs/version-control/features/binary-sync/). 

## Overview

The Unreal Binary Sync system consists of several Python scripts that work together to:
- Compile Unreal Engine binaries
- Package binaries into ZIP files
- Upload/download binaries to/from shared storage (S3 or local folders)
- Sync binaries based on Git commit tags
- Manage project dependencies and setup

## How It Works

### Core Concept
The system uses **Git tags** to mark commits that have associated compiled binaries. When a binary is built and uploaded, a unique Git tag is created on that commit. Team members can then sync to any tagged commit and automatically download the corresponding binaries.

### Tag Pattern System
- Git tags must be unique, so we use a pattern-based naming system
- Example: `Editor-1`, `Editor-2`, `Editor-3`, etc.
- The base pattern (e.g., "Editor") is configurable
- Numbers are automatically appended to ensure uniqueness

## Setup Instructions

### 1. Enable the Action
1. Go to **Workspace Settings** → **Actions**
2. Enable the Unreal Binary Sync action
3. Access the action **Settings**

### 2. Configure Shared Settings (Team-wide)
These settings apply to your entire team:

#### Tag Pattern
- Set the base name for your binary tags (e.g., "Editor", "Game", "Build")
- The system will append numbers automatically (Editor-1, Editor-2, etc.)

#### Binary Location Type
Choose your storage solution:

**Option A: S3 Storage (Recommended for larger teams)**
- Select "S3" as binary location type
- Configure S3 credentials at the bottom of settings:
  - Access Key
  - Secret Key
  - Endpoint URL
  - Bucket Name
- Benefits: Scalable, no local storage setups for team members

**Option B: Shared Folder (Good for small teams)**
- Select "Folder" as binary location type
- Use Google Drive, OneDrive, or network share
- Requirements: All team members need access to the shared folder
- Each user must configure their local path to the shared folder

### 3. Configure Project Settings (Per-user)
These settings are specific to each user's setup:

#### For Engine Built from Source:
- **Setup Dependencies**: Enable to run setup.bat and install Unreal Engine prerequisites (only relevant when you build the engine from source)
- **Launch Project**: Select which .uproject file to launch (useful when multiple projects exist)
- **Enable Binary Sync on Pull**: Automatically sync binaries when pulling Git changes
- **Binary Source Folder**: Point to your local path of the shared folder (if using folder storage)

#### For Engine from Epic Games Launcher:
- **Add Binary Push Button**: Enable to allow pushing binaries from local builds
- **Launch Project**: Usually only one project available
- **Enable Binary Sync on Pull**: Automatically sync binaries when pulling Git changes

## Usage

### Pulling Binaries
1. Pull your Git repository to the desired commit
2. Click the **"Pull Binaries"** button in Anchorpoint
3. The system will:
   - Search commit history for tags matching your pattern
   - Find the most recent tagged commit (by looking at the Git tag)
   - Download and extract the corresponding binaries
   - Optionally run setup scripts and launch the project

### Pushing Binaries
This is only applicable when you use the Engine from the Epic Games Launcher and you only want to sync game binaries with your team.
1. Ensure your project is compiled (or let the system compile it)
2. Click the **"Push Binaries"** button
3. The system will:
   - Compile binaries if needed
   - Package binaries into a ZIP file
   - Upload to your configured storage location
   - Create a Git tag on the current commit

## File Structure

```
unreal_binary_sync/
├── pull_binaries.py                     # Main sync functionality (pull binaries)
├── push_binaries.py                     # Binary compilation and submission (push binaries)
├── compile_binaries.py                  # Core binary compilation logic
└── auto_pull_hook.py                    # Trigger the pull when another event happened (a successful Git push)
└── push_binary_button_state_hook.py     # Enable/ Disable the Push Binaries sidebar button based on the project settings
```

## Files and Functions

### sync_binaries.py
**Main script for downloading and syncing binaries from storage.**

**Key Functions:**
- `sync_binaries_async()` - Main orchestration function for the sync process
- `get_commit_history()` - Retrieves Git commit history with tags
- `get_matching_commit_id()` - Finds commits with matching tag patterns
- `download_from_s3()` - Downloads binary ZIP files from S3 storage
- `unzip_and_manage_files()` - Extracts binaries and manages file tracking
- `run_setup()` - Executes Unreal Engine setup and prerequisite installation
- `is_unreal_running()` - Checks if Unreal Editor is currently running
- `find_uproject_files()` - Locates .uproject files in the project directory
- `launch_editor()` - Launches the Unreal Editor with the specified project

### submit_binaries.py
**Script for compiling, packaging, and uploading binaries.**

**Key Functions:**
- `compile_binaries()` - Compiles Unreal Engine binaries using UnrealBuildTool
- `create_binaries_zip()` - Creates ZIP archive of compiled binaries and plugins
- `get_git_commit_id()` - Gets the current Git commit hash for naming
- `find_uproject_file()` - Searches for .uproject files in project hierarchy
- `submit_binaries_async()` - Main function orchestrating the submission process

### compile_binaries.py
**Core binary compilation functionality (standalone version).**

**Key Functions:**
- `compile_binaries()` - Executes UnrealBuildTool to compile project binaries
- `create_binaries_zip()` - Packages binaries into ZIP with commit-based naming
- `get_git_commit_id()` - Retrieves Git commit hash for version tracking
- `find_uproject_file()` - Locates project files in directory tree

## Technical Details

### Binary Storage Format
- Binaries are stored as ZIP files named with Git commit hashes (e.g., `a1b2c3d4e5f6...zip`)
- ZIP files contain:
  - Main project binaries (`Binaries/Win64/`)
  - Plugin binaries (`Plugins/*/Binaries/Win64/`)
  - Excludes debug files (.pdb, .exp) to reduce file size

### File Tracking
- `extracted_binaries.txt` tracks which files were extracted from each sync
- Enables clean removal of old binaries before extracting new ones
- First line contains the source ZIP filename for version tracking

### Error Handling
- Comprehensive error messages for common issues
- Graceful fallbacks for missing dependencies
- User cancellation support for long-running operations

### Platform Support
- Currently optimized for Windows (Win64 binaries)
- Uses Windows-specific paths and executables
- CMD compatibility

## Troubleshooting

### Common Issues

**No .uproject file found**
- Ensure you're running the action from an Unreal Engine project directory
- Check that .uproject files exist in the project or subdirectories

**No compatible tag found**
- Verify your tag pattern matches existing Git tags
- Check that tagged commits exist in your repository
- Ensure Git tags follow the pattern format (e.g., Editor-1, Editor-2)

**UnrealBuildTool not found**
- Verify the Engine Directory path in project settings
- Ensure Unreal Engine is properly installed
- Check that the specified version exists

**S3 Download Issues**
- Verify S3 credentials are correct
- Check bucket name and permissions
- Ensure endpoint URL is properly formatted

**Binary Sync on Pull Not Working**
- Verify the setting is enabled in project settings
- Check that you're pulling to a commit with tagged binaries
- Ensure tag pattern matches your repository's tags

### Debug Mode
Anchorpoint provides console output for debugging:
- Enable "Show Console" in the top right corner of Anchorpoint to see detailed progress information
- Monitor Git operations, file extraction, and compilation steps
- Check for specific error messages and file paths

## Requirements

- Unreal Engine installation
- Access to shared storage (S3 or shared folder)
- Anchorpoint workspace with appropriate permissions