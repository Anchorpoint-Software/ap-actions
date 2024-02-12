import anchorpoint as ap
import apsync as aps
import vc.apgit_utility.install_git as install_git
import os

# Returns True if any executable is running
def is_executable_running(names: list[str]):
    import psutil
    for p in psutil.process_iter(attrs=['name']):
        try:
            if len(p.name()) > 0 and p.name().lower() in names:
                return True 
        except:
            continue
    return False

def is_git_running():
    try:
        return is_executable_running(["git", "git.exe"])
    except Exception as e:
        return True # Expect it to be running
    
def get_locking_application(path: str):
    import psutil
    for process in psutil.process_iter():
        try:
            if process.name() in ["svchost.exe", "conhost.exe", "explorer.exe", "wsl.exe", "wslhost.exe", "runtimebroker.exe", "crashpad_handler.exe", "chrome.exe"]:
                continue
            for file in process.open_files():
                if path in file.path:
                    return process.name()
        except:
            pass
    return None

def make_file_writable(path: str):
    try:
        os.chmod(path, 0o666)
        return True
    except Exception as e:
        print(f"Could not make file writable: {e}")
        return False

def is_file_writable(path: str):
    try:
        if not os.path.exists(path):
            return True
        f=open(path, "a")
        f.close()
        return True
    except Exception as e:
        return False

def setup_git():
     ap.get_context().run_async(install_git.setup_git)
     return True

def get_repo_path(channel_id: str, project_path: str):
    project = aps.get_project(project_path)
    if not project: return project_path
    channel = aps.get_timeline_channel(project, channel_id)
    if not channel: return project_path
    if not "gitPathId" in channel.metadata: return project_path
    try:
        folder = aps.get_folder_by_id(channel.metadata["gitPathId"], project)
    except:
        return project_path
    if not folder: return project_path
    return folder

def get_repo_url_from_channel(channel_id: str, workspace_id: str, project_id: str):
    try:
        project = aps.get_project_by_id(project_id, workspace_id)
    except Exception as e:
        print(f"get_repo_url_from_channel failed with {str(e)}")
        return None
    if not project: return None
    channel = aps.get_timeline_channel(project, channel_id)
    if not channel: return None
    if not "gitRemoteUrl" in channel.metadata: return None
    return channel.metadata["gitRemoteUrl"]