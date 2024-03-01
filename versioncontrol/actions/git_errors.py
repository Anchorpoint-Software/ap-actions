from typing import Optional
import anchorpoint as ap
import platform
import sys
import os

script_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, script_dir)
import vc.apgit.utility as utility
from vc.apgit.repository import GitRepository
from vc.models import HistoryType

if script_dir in sys.path:
    sys.path.remove(script_dir)


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
                    return "../" + splits[-2] + "/" + filename
                else:
                    return splits[-2] + "/" + filename

    return file


def _apply_azure_ipv4(d, ip_address, hostname):
    import tempfile
    import subprocess

    d.close()
    temp_dir = tempfile.gettempdir()
    batch_script = os.path.join(temp_dir, "Anchorpoint Azure DevOps Setup.bat")
    python_script = os.path.join(temp_dir, "run_elevated.py")

    batch_script = batch_script.replace("\\", "/")

    script_content = "@echo off\n"
    script_content += "echo # Workaround for IPv6 issue for dev.azure.com, added by Anchorpoint >> C:\\Windows\\System32\\drivers\\etc\\hosts\n"
    script_content += (
        f"echo {ip_address} {hostname} >> C:\\Windows\\System32\\drivers\\etc\\hosts\n"
    )
    script_content += "ping -n 2 127.0.0.1 > nul\n"  # Pause for a short duration

    with open(batch_script, "w") as f:
        f.write(script_content)

    script_content = "import ctypes\n"
    script_content += f'result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "{batch_script}", None, None, 0)\n'
    script_content += "if int(result) <= 32: sys.exit(1)\n"

    with open(python_script, "w") as f:
        f.write(script_content)

    try:
        print(f"Patching hosts file to use IPv4 for dev.azure.com ({ip_address})")
        result = subprocess.call(
            [sys.executable, python_script], creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result != 0:
            ap.UI().show_error("Failed to run AzureDevops setup script as administator")
            return
        ap.UI().show_info("Setup Finished", "Please retry the operation", duration=4000)
    finally:
        os.remove(batch_script)
        os.remove(python_script)


def _handle_azure_ipv6():
    import platform
    import socket

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
        d.add_text(
            "May Anchorpoint apply the change for you?\nWindows will ask you for permission."
        )
        d.add_info(
            'Learn more about <a href="https://docs.anchorpoint.app/docs/version-control/troubleshooting/#azure-devops-network-configuration">Azure DevOps network configuration</a>'
        )
        d.add_button(
            "Continue", callback=lambda d: _apply_azure_ipv4(d, ipv4_address, hostname)
        )
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
        print(
            "No repository path provided for clear credentials in repository not found error"
        )
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
        d.add_info(
            "If you're using our GitHub integration, try disconnecting and connecting it again.<br>If you are not using the GitHub integration, check if you are logged in with the correct GitHub account."
        )
    else:
        d.add_info(
            'Most likely you are logged in with a wrong Git account or do not have access.<br>Update credentials or check our <a href="https://docs.anchorpoint.app/docs/3-work-in-a-team/git/5-Git-troubleshooting/">troubleshooting</a> for help.'
        )

    try:
        repo = GitRepository.load(repo_path)
        if repo:
            d.add_button(
                "Update Credentials",
                var="updatecreds",
                callback=lambda d: clear_credentials(d, repo_path),
                primary=False,
            )
        else:
            d.add_button("OK", callback=lambda d: d.close())
    except:
        d.add_button("OK", callback=lambda d: d.close())
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
        show_invalid_credentials_error(
            "Your repository was not found",
            f"The URL {url}<br>cannot be found under your account.",
            repo_path,
            url,
        )
        return True

    return False


def show_unable_to_access_error(message, repo_path):
    def extract_repository_url(input_string):
        import re

        pattern = r"unable to access '([^']+)'"
        matches = re.findall(pattern, input_string)
        if matches:
            return matches[0]
        return None

    url = extract_repository_url(message)
    context = ap.get_context()
    if not context:
        return False

    if url:
        show_invalid_credentials_error(
            "Could not access repository",
            f"The URL {url} cannot be accessed.",
            repo_path,
            url,
        )
        return True

    return False


def fix_username(repo_path):
    if not repo_path:
        return False

    repo = GitRepository.load(repo_path)
    if not repo:
        return False

    context = ap.get_context()
    if not context:
        return False

    repo.set_username(context.username, context.email, repo_path)
    return True


def create_push_logfiles_async(repo_path, dialog):
    try:
        repo = GitRepository.load(repo_path)
        if not repo:
            print(f"create_push_logfiles: Failed to load repository {repo_path}")
            return

        progress = ap.Progress(
            "Creating Log File", "This can take a while", show_loading_screen=True
        )
        repo.create_push_log()
        ap.UI().show_success(
            "Log file created",
            duration=10000,
        )
    except Exception as e:
        msg = str(e)
        if "git lfs push successful" in msg:
            print("create_push_logfiles: LFS push successful (unexpected)")
            ap.UI().show_success(
                "LFS push successful",
                "Please try pushing to AzureDevOps again",
                duration=50000,
            )
            dialog.close()
            return
        print(f"Failed to create push log files: {msg}")
        ap.UI().show_error(
            "Failed to create push log files",
            'Please <a href="ap://sendfeedback">send us a message</a>',
            duration=50000,
        )


def create_push_logfiles(repo_path, dialog):
    ctx = ap.get_context()
    ctx.run_async(create_push_logfiles_async, repo_path, dialog)


def remove_file_from_commit_async(rel_filepath, repo_path, dialog):
    try:
        repo = GitRepository.load(repo_path)
        if not repo:
            print(f"remove_file_from_commit: Failed to load repository {repo_path}")
            return

        changes = repo.get_pending_changes(staged=True)
        if changes.size() != 0:
            print(f"remove_file_from_commit: Staged changes found {changes.size()}")
            ap.UI().show_error(
                "Failed to remove file from commit",
                "You have staged changes, please unstage them and try again.",
                duration=10000,
            )
            return

        history = repo.get_history(path=rel_filepath)
        if len(history) == 0:
            print(f"remove_file_from_commit: No history found for {rel_filepath}")
            return

        first_commit = history[0]
        head = repo.get_current_change_id()
        if first_commit.id != head:
            print(
                f"remove_file_from_commit: File {rel_filepath} is not in the current commit"
            )
            ap.UI().show_error(
                "Failed to remove file from commit",
                "The file is not in the current commit, please try a different approach.",
                duration=10000,
            )

            return

        if first_commit.type != HistoryType.LOCAL:
            print(
                f"remove_file_from_commit: File {rel_filepath} is already pushed {first_commit.type}"
            )
            ap.UI().show_error(
                "Failed to remove file from commit",
                "The file is already pushed, please try a different approach.",
                duration=10000,
            )

            return

        repo.remove_files([rel_filepath], cache_only=True)

        try:
            repo.commit(message=None, amend=True)
        except Exception as e:
            msg = str(e)
            if (
                "You asked to amend the most recent commit, but doing so would make"
                in msg
            ):
                repo.reset(commit_id="HEAD^")
            else:
                raise e

        dialog.close()
        ap.reload_timeline_entries()
        ap.vc_load_pending_changes("Git", True)
        ap.UI().show_success(
            "Removed file from commit",
            "Please try pushing again",
            duration=10000,
        )

    except Exception as e:
        print(f"Failed to remove file from commit: {str(e)}")
        ap.UI().show_error(
            "Failed to remove file from commit",
            duration=50000,
        )


def remove_file_from_commit(rel_filepath, repo_path, dialog):
    ctx = ap.get_context()
    ctx.run_async(remove_file_from_commit_async, rel_filepath, repo_path, dialog)


def handle_azure_upload_bug(repo_path, error_message):
    import webbrowser

    ap.log_error(f"handle_azure_upload_bug: {error_message}")

    def extract_filehash():
        import re

        pattern = r"lfs/objects/([0-9a-f]+)"
        matches = re.findall(pattern, error_message)
        if matches:
            return matches[0]
        return None

    filehash = extract_filehash()
    if not filehash:
        print(
            f"handle_azure_upload_bug: Could not extract filehash from {error_message}"
        )
        return False

    lfs_file = os.path.join(
        repo_path, ".git", "lfs", "objects", filehash[:2], filehash[2:4], filehash
    )
    if not os.path.exists(lfs_file):
        print(f"handle_azure_upload_bug: Could not find LFS file {lfs_file}")
        return False

    file_size = os.path.getsize(lfs_file)
    file_size_gb = file_size / 1024 / 1024 / 1024

    repo = GitRepository.load(repo_path)
    if not repo:
        print(f"handle_azure_upload_bug: Could not load repository {repo_path}")
        return False

    rel_file = repo.get_file_from_hash(filehash)
    if not rel_file:
        print(f"handle_azure_upload_bug: Could not find file for hash {filehash}")
        return False

    log_path = os.path.join(repo_path, "azure_bug.log")

    dialog = ap.Dialog()
    dialog.title = "Azure DevOps Upload Failed"
    dialog.icon = ":/icons/versioncontrol.svg"
    dialog.add_text(
        f"The file <b>{rel_file}</b> could not be uploaded to Azure DevOps."
    )
    dialog.add_text(
        "This is a known issue with Azure DevOps. To help them fix this, please create a bug report."
    )

    dialog.start_section("How to create a bug report", folded=True)
    dialog.add_text("1. Create log files for Microsoft Support (can take a while)")
    dialog.add_button(
        "Create Log Files",
        primary=False,
        callback=lambda d: create_push_logfiles(repo_path, d),
    )
    dialog.add_text("2. Create a bug report on Azure DevOps")
    dialog.add_button(
        "Create Bug Report",
        primary=False,
        callback=lambda d: webbrowser.open_new(
            "https://developercommunity.visualstudio.com/AzureDevOps/report"
        ),
    )
    dialog.add_text(
        "3. Provide a clear title: <b>Git LFS push fails with error code 503 'MISSING'</b>"
    )
    dialog.add_text(
        f"4. Describe that you cannot push a git LFS file of {file_size_gb:.2f} GB.<br>Refer to this related support request ID: <b>2302070050000873</b>"
    )
    dialog.add_text("5. Attach the log files you created in step 1")
    dialog.add_info(f"You can find the log file here:<br>{log_path}")
    dialog.end_section()

    dialog.add_text("To unblock you from working, you can try to:")
    dialog.add_empty().add_text("• Create a new project and exclude the file")
    dialog.add_empty().add_text("• Create a new Azure DevOps organization")
    dialog.add_empty().add_text(
        "• Let Anchorpoint try to remove the file from your commit"
    )

    dialog.add_empty().add_button(
        "Remove file from commit",
        callback=lambda d: remove_file_from_commit(rel_file, repo_path, d),
    )
    dialog.show()

    return True


def handle_error(e: Exception, repo_path: Optional[str] = None):
    message = str(e)
    print(f"handle_error: {message}")

    if (
        "warning: failed to remove" in message
        or "error: unable to unlink" in message
        or "error: unable to index file" in message
    ):
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
        d.title = (
            "Git: Could not Save Files" if isread else "Git: Could not Change Files"
        )
        d.icon = ":/icons/versioncontrol.svg"

        if not file:
            user_error = f"Some file could not be {operation} because it is opened by an application,<br>or you don't have permissions to {permission} the file."
        elif application:
            user_error = f"The file <b>{file}</b> could not<br>be {operation} because it is opened by an application (probably <i>{application}</i>).<br>Please close {application} and try again."
        else:
            user_error = f"The file <b>{file}</b><br> could not be {operation} because it is opened by an application,<br>or you don't have permissions to {permission} the file."

        d.add_text(user_error)
        if platform.system() == "Darwin":
            d.add_info(
                "Please close the application or fix the permissions and try again.<br>See more details in the Python console <b>(CMD+SHIFT+P)</b>"
            )
        else:
            d.add_info(
                "Please close the application or fix the permissions and try again.<br>See more details in the Python console <b>(CTRL+SHIFT+P)</b>"
            )

        d.add_button("OK", callback=lambda d: d.close())
        d.show()

        print(f"Showing Dialog: {user_error}")

        return True

    if "Stash on branch" in message:
        ap.UI().show_info(
            "You already have shelved files",
            "Commit your changed files and then try again",
            duration=10000,
        )
        return True

    if "The following untracked working tree files would be overwritten by" in message:
        ap.UI().show_info(
            "Files would be deleted",
            'This operation would delete files and we are not sure if this is intended. To clean your repository use the "revert" command instead.',
        )
        return True

    if "Not a git repository" in message:
        ap.UI().show_info(
            "Not a git repository",
            'This folder is not a git repository. Check our <a href="https://docs.anchorpoint.app/docs/version-control/troubleshooting/">troubleshooting</a> for help.',
            duration=6000,
        )
        return True

    if (
        "Connection was reset" in message
        and "fatal: unable to access" in message
        and "dev.azure" in message
    ):
        # azure fails to work with ipv6 in some cases: https://stackoverflow.com/questions/67230241/fatal-unable-to-access-https-dev-azure-com-xxx-openssl-ssl-connect-connec
        return _handle_azure_ipv6()

    if (
        "index file corrupt" in message
        or "unknown index entry format" in message
        or "cache entry out of order" in message
    ):
        restore_corrupted_index()
        return True

    if "fatal: repository" in message and "not found" in message:
        return show_repository_not_found_error(message, repo_path)

    if "could not read Password" in message or "Authentication failed" in message:
        show_invalid_credentials_error(
            "Invalid Git Credentials",
            "Your Git credentials are invalid. Please update them.",
            repo_path,
            None,
        )
        return True

    if "organization has enabled or enforced SAML SSO" in message:
        show_invalid_credentials_error(
            "Please re-authenticate",
            "Your organization has enabled or enforced SAML SSO. Please re-authenticate.",
            repo_path,
            None,
        )
        return True

    if "Could not read from remote repository" in message:
        show_invalid_credentials_error(
            "Could not read from remote repository",
            "Please make sure you have the correct access rights and the repository exists.",
            repo_path,
            None,
        )
        return True

    if "stash entry is kept" in message:
        # ignore
        return False

    if "unable to access" in message:
        if show_unable_to_access_error(message, repo_path):
            return True

    if "Another Git repository found in" in message:
        ap.UI().show_error("Another Git repository found", message, duration=10000)
        return True

    if (
        "no space left on device" in message
        or "not enough space" in message
        or "out of disk space" in message
        or "not enough memory" in message
        or "could not write config file" in message
        or "Out of memory" in message
    ):
        ap.UI().show_error("No space left on device", message, duration=10000)
        return True

    if "LFS object not found" in message:
        ap.UI().show_error(
            "Missing File",
            'An object is missing on the server, learn <a href="https://docs.anchorpoint.app/docs/version-control/troubleshooting/#missing-file">how to fix</a> this.',
            duration=10000,
        )
        return True

    if (
        "lfs/objects/" in message
        and "(MISSING) from HTTP 503" in message
        and "Fatal error: Server error" in message
    ):
        if handle_azure_upload_bug(repo_path, message):
            return True

    if "detected dubious ownership in repository" in message:
        if repo_path:
            repo = GitRepository.load(repo_path)
            if repo:
                repo.set_safe_directory(repo_path)
        else:
            ap.UI().show_error(
                "Detected dubious ownership in repository", message, duration=10000
            )
        return True

    if (
        "Couldn't connect to server" in message
        or "Could not resolve host" in message
        or "Timed out" in message
        or "Connection refused" in message
        or "no such host" in message
    ):
        # Extract the repo URL
        import re

        match = re.search(r"unable to access '(.*?)':", message)
        if match:
            repo_url = match.group(1)
            error_message = f'The repository "{repo_url}" cannot be reached. Check your internet connection, contact your server admin for more information or check our <a href="https://docs.anchorpoint.app/docs/version-control/troubleshooting/">git troubleshooting</a>.'
        else:
            error_message = 'The repository cannot be reached. Check your internet connection, contact your server admin for more information or check our <a href="https://docs.anchorpoint.app/docs/version-control/troubleshooting/">git troubleshooting</a>.'

        ap.UI().show_error(
            "Couldn't connect to repository", error_message, duration=10000
        )
        return True

    if "This repository is over its data quota" in message:
        ap.UI().show_error(
            "The GitHub LFS limit has been reached",
            'To solve the problem open your GitHub <a href="https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage">Billing and Plans</a> page and buy more <b>Git LFS Data</b>.',
            duration=10000,
        )
        return True

    if "CONFLICT" in message:
        return False

    if "MERGE_HEAD exists" in message:
        if repo_path:
            repo = GitRepository.load(repo_path)
            if repo:
                if repo.has_conflicts():
                    ap.UI().show_error(
                        "Merge in progress",
                        "A merge is in progress, please resolve the conflicts and continue.",
                        duration=10000,
                    )
                else:
                    ap.UI().show_error(
                        "Merge in progress",
                        "Commit your changes and continue",
                        duration=10000,
                    )
            return True
        ap.UI().show_error(
            "Merge in progress",
            "A merge is in progress, please resolve the conflicts and continue.",
            duration=10000,
        )
        return True

    if "Failed to find location service" in message:
        ap.UI().show_error(
            title="Cannot store Azure DevOps credentials",
            duration=10000,
            description='Please visit our <a href="https://docs.anchorpoint.app/docs/general/integrations/azure-devops/#could-not-store-credentials">troubleshooting</a> page to learn how to fix this.',
        )
        return True

    if "User canceled authentication" in message:
        ap.UI().show_info(
            "User canceled authentication",
            "The authentication was canceled by the user.",
            duration=10000,
        )
        return True

    if "unmerged" in message or "not concluded your merge" in message:
        ap.UI().show_error(
            "Conflict Detected",
            'A file is conflicting, use "Resolve Conflicts" to continue.',
            duration=10000,
        )
        return True

    if "unable to write new_index file" in message:
        ap.UI().show_error(
            "Could not apply changes",
            "Maybe you are out of disk space?",
            duration=10000,
        )
        return True

    if "name consists only of disallowed characters" in message:
        fix_username(repo_path)
        return False  # Still show original error to user

    if ".git/index.lock" in message:
        if repo_path:
            repo = GitRepository.load(repo_path)
            if repo:
                try:
                    repo.check_index_lock()
                    ap.UI().show_error(
                        "Could not apply change", "Please try again", duration=10000
                    )
                    return True
                except:
                    print(
                        f"Failed to remove index.lock in {repo_path}. Error: {message}"
                    )
                    return False

    if (
        "git-lfs filter-process" in message
        and "git lfs logs last" in message
        and repo_path
    ):
        repo = GitRepository.load(repo_path)
        if repo:
            log = repo.create_lfs_log()
            print(f"git lfs logs last: {log}")
            pass  # Continue to show the original error

    if "pathspec" in message and "did not match any file" in message:
        match = re.match(r"error: pathspec '(.*)' did not match any file", message)
        if match:
            file = match.group(1)
            ap.UI().show_error(
                "File not found",
                f"The file <b>{file}</b> could not be found.",
                duration=10000,
            )
            return True

    if (
        "failed due to: exit code" in message
        or "has no refspec set" in message
        or "clean filter 'lfs' failed" in message
        or "bad config line" in message
        or "(MISSING) from HTTP 503" in message
    ):

        def extract_first_fatal_error(error_message):
            try:
                lines = error_message.split("\n")
                for line in lines:
                    if (
                        "git-credential-manager-core was renamed to git-credential-manager"
                        in line
                    ):
                        continue

                    if "fatal: " in line:
                        return line.split("fatal: ")[-1].strip()

                    if "error: " in line:
                        return line.split("error: ")[-1].strip()
            except:
                return None
            return None

        error = extract_first_fatal_error(message)
        msg = 'In order to help you as quickly as possible, you can <a href="ap://sendfeedback">send us a message</a>. We will get back to you by e-mail.'
        if error:
            ap.log_error(f"Unhandled Git Error: {error}")
            if len(error) > 50:
                error = error[:50] + "..."
            ap.UI().show_error(
                "An issue has occured", f"{error}<br><br>{msg}", duration=10000
            )
        else:
            ap.log_error(f"Unhandled Git Error: {message}")
            ap.UI().show_error("An issue has occured", msg, duration=10000)

        return True

    return False
