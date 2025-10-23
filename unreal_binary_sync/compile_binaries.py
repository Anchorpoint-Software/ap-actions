#!/usr/bin/env python3
"""
Python script to compile Unreal Engine binaries for a project.
Equivalent to the PowerShell script for building Unreal Engine projects.
"""

import subprocess
import sys
import os
import zipfile
from pathlib import Path
from datetime import datetime


def compile_binaries(project_dir,project_name):
    # Hardcoded variables - modify these as needed
    engine_dir = Path(r"C:\Program Files\Epic Games\UE_5.6")  # Path to Unreal Engine installation
    editor_target = "Harbor_DemoEditor"  # Editor target to build
    
    print(f"Compiling Binaries for project {project_name} at {project_dir}, using Engine at {engine_dir}")
    
    # Path to UnrealBuildTool
    unreal_build_tool = engine_dir / "Engine" / "Binaries" / "DotNET" / "UnrealBuildTool" / "UnrealBuildTool.exe"
    
    # Path to project file
    project_file = project_dir / f"{project_name}.uproject"
    
    # Verify paths exist
    if not unreal_build_tool.exists():
        print(f"Error: UnrealBuildTool not found at {unreal_build_tool}", file=sys.stderr)
        sys.exit(1)
        
    if not project_file.exists():
        print(f"Error: Project file not found at {project_file}", file=sys.stderr)
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
        # Execute the command
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"Build completed successfully with exit code {result.returncode}")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
        
    except FileNotFoundError:
        print(f"Error: Could not execute {unreal_build_tool}", file=sys.stderr)
        sys.exit(1)


def get_git_commit_id(project_dir):
    """
    Get the latest commit ID from the git repository.
    
    Args:
        project_dir (Path): Path to the project directory
        
    Returns:
        str: Full commit ID (40 characters) or 'unknown' if not available
    """
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
        print("Warning: Could not get git commit ID (not a git repository or git not found)")
        return 'unknown'
    except FileNotFoundError:
        print("Warning: Git not found in PATH")
        return 'unknown'


def create_binaries_zip(project_dir, project_name):
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
    
    # Get desktop path
    desktop_path = Path.home() / "Desktop"
    
    # Get commit ID for filename
    commit_id = get_git_commit_id(project_dir)
    zip_filename = f"{commit_id}.zip"
    zip_path = desktop_path / zip_filename
    
    # Check if file exists and inform about overwrite
    if zip_path.exists():
        print(f"File already exists and will be overwritten: {zip_path}")
    else:
        print(f"Creating new ZIP file: {zip_path}")
    
    print(f"Creating ZIP archive of Binaries folders...")
    print(f"Main binaries: {binaries_dir if binaries_dir.exists() else 'Not found'}")
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
                            print(f"Skipped: {file_path.relative_to(project_dir)} (excluded extension)")
                            continue
                        
                        # Calculate relative path for the archive
                        arc_name = file_path.relative_to(project_dir)
                        zipf.write(file_path, arc_name)
                        print(f"Added: {arc_name}")
        
        print(f"Successfully created ZIP archive: {zip_path}")
        print(f"Archive size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"Error creating ZIP archive: {e}", file=sys.stderr)


def main():
    # Hardcoded variables - modify these as needed
    project_dir = Path(r"D:\Repositories\Unreal\UE5_Harbor_Demo")  # Path to your project directory
    project_name = "Harbor_Demo"  # Name of your project
    
    compile_binaries(project_dir, project_name)
    create_binaries_zip(project_dir, project_name)

if __name__ == "__main__":
    main()