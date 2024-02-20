from subprocess import call
from typing import Optional
import anchorpoint as ap
import platform, sys, os

script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)
import vc.apgit.utility as utility
from vc.apgit.repository import GitRepository
if script_dir in sys.path: sys.path.remove(script_dir)

def _guess_application(file: str):
    known_applications = {
        ".uasset": "Unreal Engine",
        ".umap": "Unreal Engine",
        
        ".meta": "Unity3D",
        ".unity": "Unity3D",
        ".unitypackage": "Unity3D",
        ".prefab": "Unity3D",
        
        ".blend": "Blender",
        ".c4d": "Cinema 4D",
        ".psd": "Photoshop",
        ".indd": "InDesign",
        ".idlk": "InDesign",
        ".ai": "Illustrator",
        ".skp": "SketchUp",
        ".3ds": "3DS Max",
        ".max": "3DS Max",
        ".fbx": "3DS Max",
        ".dae": "3DS Max",
        ".obj": "3DS Max",
        ".stl": "3DS Max",
        ".ma": "Maya",
        ".mb": "Maya",
    }

    for ext in known_applications:
        if ext in file:
            return known_applications[ext]
    return None

def _get_file_from_error(error_message: str):
    import re
    try:
        matches = re.findall(r"(?<=\s')[^']+(?=')", error_message)
        for match in matches:
            if "error" in match or "warning" in match:
                continue
            return match
    except:
        return None
    
def _shorten_filepath(file: str):
    max_length = 50
    file = file.replace("\\", "/")
    if file and len(file) > max_length:
        splits = file.split("/")
        if len(splits) > 1:
            filename = splits[-1]
            if len(filename) > max_length:
                return "../" + filename
            else:
                if len(splits) > 2:
                    return "../" + splits[-2] + "/"+ filename
                else:
                    return splits[-2] + "/"+ filename

    return file

def _apply_azure_ipv4(d, ip_address, hostname):
    import tempfile, subprocess

    d.close()
    temp_dir = tempfile.gettempdir()
    batch_script = os.path.join(temp_dir, "Anchorpoint Azure DevOps Setup.bat")
    python_script = os.path.join(temp_dir, "run_elevated.py")

    batch_script = batch_script.replace("\\","/")

    script_content = f'@echo off\n'
    script_content += f'echo # Workaround for IPv6 issue for dev.azure.com, added by Anchorpoint >> C:\\Windows\\System32\\drivers\\etc\\hosts\n'
    script_content += f'echo {ip_address} {hostname} >> C:\\Windows\\System32\\drivers\\etc\\hosts\n'
    script_content += f'ping -n 2 127.0.0.1 > nul\n'  # Pause for a short duration

    with open(batch_script, 'w') as f:
        f.write(script_content)

    script_content = f'import ctypes\n'
    script_content += f'result = ctypes.windll.shell32.ShellExecuteW(None, \"runas\", \"{batch_script}\", None, None, 0)\n'
    script_content += f'if int(result) <= 32: sys.exit(1)\n'

    with open(python_script, 'w') as f:
        f.write(script_content)

    try:
        print(f"Patching hosts file to use IPv4 for dev.azure.com ({ip_address})")
        result = subprocess.call([sys.executable, python_script], creationflags=subprocess.CREATE_NO_WINDOW)
        if result != 0:
            ap.UI().show_error("Failed to run AzureDevops setup script as administator")
            return
        ap.UI().show_info("Setup Finished", "Please retry the operation", duration=4000)
    finally:
        os.remove(batch_script)
        os.remove(python_script)

def _handle_azure_ipv6():
    import platform, socket
    if platform.system() != "Windows":
        print("Error: IPv6 error for dev.azure.com but not on Windows")
        return False

    hostname = "dev.azure.com"
    def _entry_exists(ipv4_address):
        try:
            with open(r"C:\Windows\System32\drivers\etc\hosts", "r") as hosts_file:
                for line in hosts_file:
                    if f"{ipv4_address} {hostname}" in line:
                        return True
        except FileNotFoundError:
            pass
        return False

    try:
        ipv4_address = socket.gethostbyname(hostname)
        if _entry_exists(ipv4_address):
            print("Error: IPv6 error for dev.azure.com but hosts file already patched")
            return False

        d = ap.Dialog()
        d.title = "Azure DevOps requires a configuration change"
        d.icon = ":/icons/versioncontrol.svg"
        d.add_text("May Anchorpoint apply the change for you?\nWindows will ask you for permission.")
        d.add_info("Learn more about <a href=\"https://docs.anchorpoint.app/docs/version-control/troubleshooting/#azure-devops-network-configuration\">Azure DevOps network configuration</a>")
        d.add_button("Continue", callback=lambda d:_apply_azure_ipv4(d, ipv4_address, hostname))
        d.show()
        
    except Exception as e:
        print(e)
        return False

    return True

def restore_corrupted_index():
    print("restoring corrupted index")
    try:
        progress = ap.Progress("Restoring Git Index", show_loading_screen=True)
        context = ap.get_context()
        if not context: 
            return

        repo_path = utility.get_repo_path("Git", context.project_path)
        if not repo_path: 
            return

        repo = GitRepository.load(repo_path)
        if not repo: 
            return

        index = os.path.join(repo.get_git_dir(), "index")
        if os.path.exists(index): 
            os.remove(index)

        repo.reset(None, False)
    except Exception as e:
        print(e)

def clear_credentials_async(dialog, repo_path: Optional[str]):
    try:
        dialog.set_processing("updatecreds", True, "Updating")
        repo = GitRepository.load(repo_path)
        if repo and repo.clear_credentials():
            repo.fetch()
            ap.UI().show_success("Credentials updated")
    finally:
        dialog.close()

def clear_credentials(dialog, repo_path: Optional[str]):
    if not repo_path:
        print("No repository path provided for clear credentials in repository not found error")
        dialog.close()
        return
    
    ctx = ap.get_context()
    ctx.run_async(clear_credentials_async, dialog, repo_path)

def show_invalid_credentials_error(title, message, repo_path, url):
    d = ap.Dialog()
    d.title = title
    d.icon = ":/icons/versioncontrol.svg"
    d.add_text(message)

    if url and "github" in url.lower():
        d.add_info("If you're using our GitHub integration, try disconnecting and connecting it again.<br>If you are not using the GitHub integration, check if you are logged in with the correct GitHub account.")
    else:
        d.add_info("Most likely you are logged in with a wrong Git account.<br>Update credentials or check our <a href=\"https://docs.anchorpoint.app/docs/3-work-in-a-team/git/5-Git-troubleshooting/\">troubleshooting</a> for help.")
    
    d.add_button("Update Credentials", var="updatecreds", callback=lambda d: clear_credentials(d, repo_path), primary=False)
    d.show()

def show_repository_not_found_error(message, repo_path):
    def extract_repository_url(input_string):
        import re
        pattern = r"repository '([^']+)' not found"
        matches = re.findall(pattern, input_string)
        if matches:
            return matches[0]
        return None
    
    url = extract_repository_url(message)
    context = ap.get_context()
    if not context: 
        return False
    
    if url:
        show_invalid_credentials_error("Your repository was not found", f"The URL {url}<br>cannot be found under your account.", repo_path, url)
        return True

    return False

def handle_error(e: Exception, repo_path: Optional[str] = None):
    message = str(e)
    print(message)

    if "warning: failed to remove" in message or "error: unable to unlink" in message or "error: unable to index file" in message:
        isread = "error: unable to index file" in message
        permission = "read" if isread else "write"
        operation = "read" if isread else "changed"
        file = _get_file_from_error(message)
        application = _guess_application(file)
        # This is too slow on Windows, unfortunately
        # if file:
        #     application = utility.get_locking_application(file)

        file = _shorten_filepath(file)
                
        d = ap.Dialog()
        d.title = "Git: Could not Save Files" if isread else "Git: Could not Change Files"
        d.icon = ":/icons/versioncontrol.svg"

        if not file:
            user_error = f"Some file could not be {operation} because it is opened by an application,<br>or you don't have permissions to {permission} the file."
        elif application:
            user_error = f"The file <b>{file}</b> could not<br>be {operation} because it is opened by an application (probably <i>{application}</i>).<br>Please close {application} and try again."
        else:
            user_error = f"The file <b>{file}</b><br> could not be {operation} because it is opened by an application,<br>or you don't have permissions to {permission} the file."

        d.add_text(user_error)
        if platform.system() == "Darwin":
            d.add_info("Please close the application or fix the permissions and try again.<br>See more details in the Python console <b>(CMD+SHIFT+P)</b>")
        else:
            d.add_info("Please close the application or fix the permissions and try again.<br>See more details in the Python console <b>(CTRL+SHIFT+P)</b>")

        d.add_button("OK", callback=lambda d: d.close())
        d.show()

        print(f"Showing Dialog: {user_error}")

        return True

    if "Stash on branch" in message:
        ap.UI().show_info("You already have shelved files", "Commit your changed files and then try again", duration=10000)
        return True

    if "The following untracked working tree files would be overwritten by" in message:
        ap.UI().show_info("Files would be deleted", "This operation would delete files and we are not sure if this is intended. To clean your repository use the \"revert\" command instead.")
        return True

    if "Not a git repository" in message:
        ap.UI().show_info("Not a git repository", "This folder is not a git repository. Check our <a href=\"https://docs.anchorpoint.app/docs/version-control/troubleshooting/\">troubleshooting</a> for help.", duration=6000)
        return True

    if "Connection was reset" in message and "fatal: unable to access" in message and "dev.azure" in message:
        # azure fails to work with ipv6 in some cases: https://stackoverflow.com/questions/67230241/fatal-unable-to-access-https-dev-azure-com-xxx-openssl-ssl-connect-connec
        return _handle_azure_ipv6()
    
    if "index file corrupt" in message or "unknown index entry format" in message or "cache entry out of order" in message:
        restore_corrupted_index()
        return True
    
    if "fatal: repository" in message and "not found" in message:
        return show_repository_not_found_error(message, repo_path)
    
    if "could not read Password" in message or "Authentication failed" in message:
        show_invalid_credentials_error("Invalid Git Credentials", "Your Git credentials are invalid. Please update them.", repo_path, None)
        return True
    
    if "Another Git repository found in" in message:
        ap.UI().show_error("Another Git repository found", message, duration=10000)
        return True
    
    if "no space left on device" in message or "not enough space" in message or "out of disk space" in message or "not enough memory" in message or "could not write config file" in message:
        ap.UI().show_error("No space left on device", message, duration=10000)
        return True
    
    if "LFS object not found" in message:
        ap.UI().show_error("Missing File", "An object is missing on the server, learn <a href=\"https://docs.anchorpoint.app/docs/version-control/troubleshooting/#missing-file\">how to fix</a> this.", duration=10000)
        return True
    
    if "detected dubious ownership in repository" in message:
        if repo_path:
            repo = GitRepository.load(repo_path)
            if repo:
                repo.set_safe_directory(repo_path)
        else:
            ap.UI().show_error("Detected dubious ownership in repository", message, duration=10000)
        return True

    if "Couldn't connect to server" in message:
        # Extract the repo URL
        import re
        match = re.search(r"unable to access '(.*?)':", message)
        if match:
            repo_url = match.group(1)
            error_message = f"The repository \"{repo_url}\" cannot be reached. Check your internet connection, contact your server admin for more information or check our <a href=\"https://docs.anchorpoint.app/docs/version-control/troubleshooting/\">git troubleshooting</a>."
            ap.UI().show_error("Couldn't connect to repository", error_message, duration=10000)
        return True
    
    if "This repository is over its data quota" in message:
        ap.UI().show_error("The GitHub LFS limit has been reached", "To solve the problem open your GitHub <a href=\"https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage\">Billing and Plans</a> page and buy more <b>Git LFS Data</b>.", duration=10000)
        return True
    
    if "Couldn't connect to server" in message or "Could not resolve host" in message or "Timed out" in message or "Connection refused" in message or "no such host" in message:
        ap.UI().show_error("Could not connect to the Git server", "Please check your internet connection and try again.", duration=10000)
        return True

    if "CONFLICT" in message:
        return False
    
    if "unmerged" in message:
        ap.UI().show_error("Confict Detected", "A file is conflicting, use \"Resolve Conflicts\" to continue.", duration=10000)
        return True

    if "unable to write new_index file" in message:
        ap.UI().show_error("Could not apply changes", "Maybe you are out of disk space?", duration=10000)
        return True

    if ".git/index.lock" in message:
        if repo_path:
            repo = GitRepository.load(repo_path)
            if repo:
                try:
                    repo.check_index_lock()
                    ap.UI().show_error("Could not apply change", "Please try again", duration=10000)
                    return True
                except:
                    print(f"Failed to remove index.lock in {repo_path}. Error: {message}")
                    return False
                
    if "failed due to: exit code" in message or "has no refspec set" in message or "clean filter 'lfs' failed'" in message:
        def extract_first_fatal_error(error_message):
            try:
                lines = error_message.split('\n')
                for line in lines:
                    if 'fatal: ' in line:
                        return line.split('fatal: ')[-1].strip()
                    
                    if 'error: ' in line:
                        return line.split('error: ')[-1].strip()
            except:
                return None
            return None
        
        error = extract_first_fatal_error(message)
        msg = "In order to help you as quickly as possible, you can <a href=\"ap://sendfeedback\">send us a message</a>. We will get back to you by e-mail."
        if error:
            if len(error) > 50:
                error = error[:50] + "..."
            ap.UI().show_error("An issue has occured", f"{error}<br><br>{msg}", duration=10000)
        else:
            ap.UI().show_error("An issue has occured", msg, duration=10000)
        return True
    
    return False