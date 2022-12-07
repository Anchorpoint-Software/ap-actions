from ast import arguments
from re import sub
import anchorpoint as ap
import apsync as aps
import platform
import subprocess
import os, sys
import json

sys.path.insert(0, os.path.dirname(__file__))
import rclone_install_helper as rclone_install
import rclone_config_helper as rclone_config

path_var = "path"
mac_mount_name = "anchorpoint"

def generate_secret_key(password: str, salt: bytes) -> str:
    from Crypto.Protocol.KDF import PBKDF2
    return PBKDF2(password, salt, dkLen=32)

def decrypt(encrypted: str, password: str) -> str:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    bytes_encrypted = bytes.fromhex(encrypted)
    iv = bytes_encrypted[:16]
    ciphered_data = bytes_encrypted[16:-32]

    salt = bytes_encrypted[-32:]
    secret_key = generate_secret_key(password, salt)

    cipher = AES.new(secret_key, AES.MODE_CBC, iv=iv) 
    original_data = unpad(cipher.decrypt(ciphered_data), AES.block_size)

    return original_data.decode()

def get_unused_drives():
    import string
    from ctypes import windll
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if not bitmask & 1:
            drives.append(letter)
        bitmask >>= 1

    return drives

def create_bat_file(command,drive):    
    app_data = os.getenv('APPDATA')
    startup_path = f'{app_data}/Microsoft/Windows/Start Menu/Programs/Startup/ap_mount_{drive}.bat'
    with open(startup_path,'w') as f:
        f.write(command)

def setup_mount(drive, workspace_id, configuration):
    def create_config_arguments():
        config = []

        #Backblaze
        if(configuration["type"]=="b2"):
            config += [
                "--b2-account",
                f"{configuration['b2_account']}", 
                "--b2-key",
                f"{configuration['b2_key']}"
                ]

        #S3 AWS
        if(configuration["type"]=="s3aws"):
            config += [
                    "--s3-provider",
                    "AWS",
                    "--s3-access-key-id",
                    f"{configuration['s3aws_access_key_id']}",
                    "--s3-secret-access-key",
                    f"{configuration['s3aws_secret_access_key']}"
                    ]
        if(configuration["s3aws_region"] and configuration["type"]=="s3aws"):
            config += ["--s3-region", f"{configuration['s3aws_region']}"]
        if(configuration["s3aws_location_constraint"] and configuration["type"]=="s3aws"):
            config += ["--s3-location-constraint",f"{configuration['s3aws_location_constraint']}"]

        #S3 Wasabi
        if(configuration["type"]=="s3wasabi"):
            config += [
                    "--s3-provider",
                    "Wasabi",
                    "--s3-access-key-id",
                    f"{configuration['s3wasabi_access_key_id']}",
                    "--s3-secret-access-key",
                    f"{configuration['s3wasabi_secret_access_key']}",
                    "--s3-endpoint",
                    f"s3.{configuration['s3wasabi_region']}.wasabisys.com",
                    "--s3-region",
                    f"{configuration['s3wasabi_region']}"
                    ]
        
        
        #Azure
        if(configuration["type"]=="azureblob"):
            config += [
                    "--azureblob-sas-url",
                    f"{configuration['azureblob_sas_url']}"
                    ]

        return config
    
    def create_location_arguments():
        #Backblaze 
        if(configuration["type"]=="b2"):
            return f":b2:{configuration['b2_bucket_name']}"

        #S3 AWS
        if(configuration["type"]=="s3aws"):
            return f":s3:{configuration['s3aws_root_folder']}"

        #S3 Wasabi
        if(configuration["type"]=="s3wasabi"):
            return f":s3:{configuration['s3wasabi_root_folder']}"

        #Azure
        if(configuration["type"]=="azureblob"):
            return f":azureblob:{configuration['azureblob_container_path']}"

    local_settings = aps.Settings("rclone")    
    cache_path = local_settings.get("cachepath",default=get_default_cache_path())

    if not os.path.isdir(cache_path):
        os.mkdir(cache_path)

    base_arguments = [
        rclone_install._get_rclone_path(),      
        "mount"
    ]    
    config_arguments = create_config_arguments()
    config_arguments.append(create_location_arguments())

    if isWin():
        config_arguments.append(f"{drive}:")
    else:
        if not os.path.isdir(drive):
            if "/Volumes" in drive:
                properties = "{name:\"%s\"}" % mac_mount_name
                args = ["/usr/bin/osascript", "-e", f"tell application \"Finder\" to make new folder at POSIX file \"/volumes\" with properties {properties}"]
                p=subprocess.Popen(
                args=args)   
                p.wait() 
            else:
                os.mkdir(drive)
        config_arguments.append(drive)

    rclone_arguments = [
        "--vfs-cache-mode",
        "full",
        "--vfs-cache-max-age",
        "10000h",
        "--vfs-read-chunk-size",
        "512M",
        "--vfs-fast-fingerprint",
        "--transfers",
        "10",
        "--network-mode",
        "--use-server-modtime",
        "--cache-dir",
        cache_path,
        "--dir-cache-time",
        "5s",
        "--volname=Anchorpoint",
        "--file-perms=0777",
        "--use-json-log",
        "--stats",
        "1s",
        "--log-level",
        "INFO"
    ]

    arguments = base_arguments + config_arguments + rclone_arguments

    ctx = ap.Context.instance()
    if isWin():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW 
        ctx.run_async(run_rclone, arguments, drive, workspace_id, startupinfo)
    else:
        #add daemon for mac
        arguments.append("--daemon")
        ctx.run_async(run_rclone, arguments, drive, workspace_id)
    
    

def dialog_setup_mount(dialog, workspace_id, configuration):
    if isWin():
        drive = dialog.get_value("drive_var")
    else:
        drive = os.path.normpath(os.path.join(dialog.get_value(path_var), mac_mount_name))
        
    setup_mount(drive, workspace_id, configuration)
    dialog.close()

def store_auto_mount(success: bool, drive: str, workspace_id: str):
    local_settings = aps.Settings(workspace_id)
    if success:
        local_settings.set("rclone-automount", True)
        local_settings.set("rclone-drive", drive)
    else:
        local_settings.remove("rclone-automount")
    local_settings.store()

def run_rclone(arguments, drive, workspace_id, startupinfo=None):
    ui = ap.UI()
    prepare_mount_progress = ap.Progress("Preparing Mount", infinite=True)
    rclone_success = "The service rclone has been started"
    rlcone_wrong_credentials = "SignatureDoesNotMatch"
    rlcone_wrong_access_key = "InvalidAccessKeyId"
    count_msg = "queuing for upload"
    upload_succeeded_msg = "upload succeeded"
    progress = None
    global_progress = ap.Progress("Mounting Cloud Drive", show_loading_screen=True)
    
    p = subprocess.Popen(
        args=arguments,
        startupinfo=startupinfo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        )
    
    count = 0
    count_uploaded = 0
    
    for line in p.stdout:
        myjson = is_json(line)
        
        if count_msg in line:
            count = add_to_count(count, 1)
        
        if upload_succeeded_msg in line:
            count_uploaded = add_to_count(count_uploaded, 1)

        if myjson != None and myjson["level"] == "error" and myjson["msg"] == "Mount failed":
            ui.show_error("Something went wrong")
            store_auto_mount(False, drive, workspace_id)
            return
        elif rclone_success in line:            
            prepare_mount_progress.finish()
            prepare_mount_progress = None
            if not isWin() and "reload_drives" in dir(ui):
                ui.reload_drives()
            store_auto_mount(True, drive, workspace_id)
            ui.show_success("Mount Successful")
            global_progress.finish()
            ui.reload()

        elif rlcone_wrong_credentials in line:
            ui.show_error(title="Invalid Settings", duration=6000, description="Your settings do not seem to be correct. Go to the settings of \"Connect Cloud Drive\" and check if you have made a typing error.")
            store_auto_mount(False, drive, workspace_id)
            return
        elif rlcone_wrong_access_key in line:
            ui.show_error(title="Invalid Settings", duration=6000, description="Your Access Key seems to be wrong. Go to the settings of \"Connect Cloud Drive\" and check if you have made a typing error.")
            store_auto_mount(False, drive, workspace_id)
            return

        if myjson and "Transferred" in myjson["msg"]:
            progress = check_upload(myjson, progress, count, count_uploaded)
            
        if progress == None:
            count = set_count_to(count, 0)
            count_uploaded = set_count_to(count_uploaded, 0)

    if not isWin() and prepare_mount_progress is not None:
        # Mac runs in daemon mode, so we assume everything has worked when we reach this point
        prepare_mount_progress.finish()
        prepare_mount_progress = None
        if not isWin() and "reload_drives" in dir(ui):
            ui.reload_drives()
        ui.show_success("Mount Successful")
        store_auto_mount(True, drive, workspace_id)
        ui.reload()
    

def is_json(myjson):
    try:
        myjson = json.loads(myjson)
    except ValueError as e:
        return
    return myjson


def check_upload(myjson, progress, count, count_uploaded):
    # get the percentage number without whitespaces
    percentage = myjson["msg"].split(",")[1].strip()
    upload_speed = myjson["msg"].split(",")[2].strip()
    
    if not progress and percentage != "100%" and percentage != "-":
        progress = ap.Progress("Syncing Files", percentage+ " at " + upload_speed, infinite=False)
    
    if progress: 
        if count > 1:
            progress.report_progress(count_uploaded/count)
            progress.set_text(str(int((count_uploaded/count)*100)) + "%" + " at " + upload_speed)
        else:
            if percentage == "-": percentage = "0"
            percentage_int = int(percentage.split("%")[0])/100
            progress.report_progress(percentage_int)
            progress.set_text(percentage + " at " + upload_speed)

    if progress and percentage == "100%":
        progress.finish()
        progress = None
    
    return progress

def set_count_to(count, number):
    count = number
    return count

def add_to_count(count, number):
    count += number
    return count

def get_default_cache_path():
    if isWin():
        app_data_roaming = os.getenv('APPDATA')
        app_data = os.path.abspath(os.path.join(app_data_roaming, os.pardir))
        return os.path.join(app_data,"Local/rclone").replace("/","\\")
    else:
        ap_cache_path = os.path.normpath(os.path.expanduser("~/library/caches/anchorpoint software/anchorpoint/rclone"))
        if not os.path.isdir(ap_cache_path):
            os.mkdir(ap_cache_path)
        return ap_cache_path

def is_admin():
    return True

def resolve_configuration(shared_settings, configuration, password):
    if shared_settings.get("Config")=="": return False

    encrypted_configuration = shared_settings.get("Config")
    decrypted_configuration = decrypt(encrypted_configuration, password)
    undumped_configuration = json.loads(decrypted_configuration)
    for i in configuration.keys():
        configuration[i] = undumped_configuration[i]

    return True

def get_settings(workspace_id: str):
    import pyperclip as pc 

    ui = ap.UI()
    shared_settings = aps.SharedSettings(workspace_id, "AnchorpointCloudMount")
    local_settings = aps.Settings("rclone")
    configuration = rclone_config.get_config()

    if shared_settings.get("Config")=="":
        if is_admin:
            ui.show_info("No cloud drive configured", description="Please setup a cloud drive in your Workspace Settings inside the Actions entry.")
        else:
            ui.show_info("No cloud drive configured", description="Ask your workspace owner to setup a cloud drive")
    else:
        password = local_settings.get("encryption_password")
        if password == None:
            create_pw_dialog(workspace_id)
        else:
            try:
                resolve_configuration(shared_settings, configuration, password)
                show_options(shared_settings.get("mount_path"), workspace_id, configuration)
            except:
                create_pw_dialog(workspace_id)

def create_pw_dialog(workspace_id: str):
    dialog = ap.Dialog()
    dialog.title = "Enter Configuration Key"
    dialog.icon = ctx.icon
    dialog.add_text("Configuration Key").add_input(placeholder="Your configuration key", var="pw_var")
    dialog.add_button("Ok", callback = lambda d: set_password(d, workspace_id))
    dialog.show()

def set_password(dialog : ap.Dialog, workspace_id: str):
    local_settings = aps.Settings("rclone")
    local_settings.set("encryption_password", dialog.get_value("pw_var"))
    local_settings.store()
    get_settings(workspace_id)

def show_options(mount_path: str, workspace_id: str, configuration):    
    ui = ap.UI()
    dialog = ap.Dialog()
    dialog.title = "Mount Cloud Drive"

    if isWin():
        drives = get_unused_drives()

        if len(drives) == 0:
            ui.show_error("No drives to mount", "Unmount another drive first")
            return

        if ctx.icon:
            dialog.icon = ctx.icon    

        dialog.add_text("Drive Letter:\t").add_dropdown(drives[0], drives, var="drive_var")
        dialog.add_button("Mount", callback=lambda d: dialog_setup_mount(d, workspace_id, configuration))

        dialog.show()
    else:
        path = mount_path
        if path ==  "":
            path = os.path.normpath("/Volumes")

        dialog.add_text("Drive Location:\t").add_input(path, browse=ap.BrowseType.Folder, var = path_var)
        dialog.add_button("Mount", callback=lambda d: dialog_setup_mount(d, workspace_id, configuration))
        dialog.show()

def isWin():
    if platform.system() == "Windows":
        return True
    return False

def on_application_started(ctx: ap.Context):
    shared_settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointCloudMount")
    mount_settings = aps.Settings(ctx.workspace_id)
    if not mount_settings.contains("rclone-automount") or not mount_settings.contains("rclone-drive"):
        return

    drive = mount_settings.get("rclone-drive")
    auto_mount = mount_settings.get("rclone-automount")
    if not auto_mount: 
        return

    if (os.path.exists(drive)):
        return

    local_settings = aps.Settings("rclone")
    configuration = rclone_config.get_config()
    password = local_settings.get("encryption_password")
    if password == None: 
        return
    try:
        resolve_configuration(shared_settings, configuration, password)
    except:
        return

    ctx.run_async(setup_mount, drive, ctx.workspace_id, configuration)
    

if __name__ == "__main__":
    ctx = ap.Context.instance()
    ctx.run_async(rclone_install.check_winfsp_and_rclone, get_settings, ctx.workspace_id)