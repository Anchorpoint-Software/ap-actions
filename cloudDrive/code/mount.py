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

ctx = ap.Context.instance()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointCloudMount")
local_settings = aps.Settings()
path_var = "path"

configuration = {
    "type": "",
    "s3_provider": "",
    "s3_access_key_id": "",
    "s3_secret_access_key": "",
    "s3_region": "",
    "s3_location_constraint": "",
    "s3_root_folder":"",
    "b2_account": "",
    "b2_key":"",
    "b2_bucket_name": ""
}

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

def setup_mount(dialog):

    def create_config_arguments():
        if(configuration["type"]=="s3"):
            return [
                    "--s3-provider",
                    f"{configuration['s3_provider']}",
                    "--s3-access-key-id",
                    f"{configuration['s3_access_key_id']}",
                    "--s3-secret-access-key",
                    f"{configuration['s3_secret_access_key']}"
                    ]
        if(configuration["type"]=="b2"):
            return [
                "--b2-account",
                f"{configuration['b2_account']}", 
                "--b2-key",
                f"{configuration['b2_key']}"
                ]
    
    def create_location_arguments():
        if(configuration["type"]=="s3"):
            return f":s3:{configuration['s3_root_folder']}"
        if(configuration["type"]=="b2"):
            return f":b2:{configuration['b2_bucket_name']}"

    settings = aps.Settings()    
    cache_path = settings.get("cachepath",default=get_default_cache_path())

    if not os.path.isdir(cache_path):
        os.mkdir(cache_path)

    base_arguments = [
        rclone_install._get_rclone_path(),      
        "mount"
    ]
    
    config_arguments = create_config_arguments()

    if(configuration["s3_region"] and configuration["type"]=="s3"):
        config_arguments.append("--s3-region")  
        config_arguments.append(f"{configuration['s3_region']}")
    if(configuration["s3_location_constraint"] and configuration["type"]=="s3"):
        config_arguments.append("--s3-location-constraint")  
        config_arguments.append(f"{configuration['s3_location_constraint']}")

    config_arguments.append(create_location_arguments())

    if isWin():
        drive = dialog.get_value("drive_var")
        config_arguments.append(f"{drive}:")
    else:
        bucket_name = "anchorpoint"
        path = os.path.normpath(os.path.join(dialog.get_value(path_var), bucket_name))
        if not os.path.isdir(path):
            if(dialog.get_value(path_var) == "/Volumes"):
                properties = "{name:\"%s\"}" % bucket_name
                args = ["/usr/bin/osascript", "-e", f"tell application \"Finder\" to make new folder at POSIX file \"/volumes\" with properties {properties}"]
                p=subprocess.Popen(
                args=args)   
                p.wait() 
            else:
                os.mkdir(path)
        config_arguments.append(path)

    rclone_arguments = [
        "--vfs-cache-mode",
        "full",
        "--vfs-cache-max-age",
        "10000h",
        "--vfs-read-chunk-size",
        "512M",
        "--transfers",
        "10",
        "--network-mode",
        "--use-server-modtime",
        "--poll-interval",
        "10s",
        "--cache-dir",
        cache_path,
        "--volname=Anchorpoint",
        "--file-perms=0777",
        "--use-json-log",
        "--stats",
        "1s",
        "--log-level",
        "INFO"
    ]

    arguments = base_arguments + config_arguments + rclone_arguments

    if isWin():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW 
        ctx.run_async(run_rclone, arguments, startupinfo)
    else:
        #add daemon for mac
        arguments.append("--daemon")
        ctx.run_async(run_rclone, arguments)
    
    dialog.close()

def run_rclone(arguments, startupinfo=None):
    prepare_mount_progress = ap.Progress("Preparing Mount", infinite=True)
    rclone_success = "The service rclone has been started"
    rlcone_wrong_credentials = "401 bad_auth_token"
    progress = None
    
    p = subprocess.Popen(
        args=arguments,
        startupinfo=startupinfo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        )
      
    for line in p.stdout:
        myjson = is_json(line)

        if myjson != None and myjson["level"] == "error" and myjson["msg"] == "Mount failed":
            ui.show_error("Something went wrong")
            print(line)
        elif rclone_success in line:            
            prepare_mount_progress.finish()
            prepare_mount_progress = None
            if not isWin() and "reload_drives" in dir(ui):
                ui.reload_drives()
            ui.show_success("Mount Successful")

        elif rlcone_wrong_credentials in line:
            ui.show_info(title="Invalid Settings", description="Your settings do not seem to be right. Go to the settings of Connect Cloud Drive and see if you made a typo.")
        elif not isWin() and prepare_mount_progress is not None:
            prepare_mount_progress.finish()
            prepare_mount_progress = None
            if not isWin() and "reload_drives" in dir(ui):
                ui.reload_drives()
            ui.show_success("Mount Successful")
        if myjson and "Transferred" in myjson["msg"]:
            progress = check_upload(myjson, progress)


def is_json(myjson):
    try:
        myjson = json.loads(myjson)
    except ValueError as e:
        return
    return myjson


def check_upload(myjson, progress):
    # get the percentage number without whitespaces
    percentage = myjson["msg"].split(",")[1].strip()
    upload_speed = myjson["msg"].split(",")[2].strip()
    
    if not progress and percentage != "100%" and percentage != "-":
        progress = ap.Progress("Syncing Files", percentage+ " at " + upload_speed, infinite=False)
    
    if progress: 
        if percentage == "-": percentage = "0"
        percentage_int = int(percentage.split("%")[0])/100
        progress.report_progress(percentage_int)
        progress.set_text(percentage + " at " + upload_speed)

    if progress and percentage == "100%":
        progress.finish()
        progress = None
    
    return progress

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

def get_settings():
    import pyperclip as pc 
    if settings.get("Config")=="":
        if is_admin:
            ui.show_info("No cloud drive configured", description="Please setup a cloud drive in your Workspace Settings inside the Actions entry.")
        else:
            ui.show_info("No cloud drive configured", description="Ask your workspace owner to setup a cloud drive")
    else:
        password = local_settings.get("encryption_password")
        if password == None:
            print("no pw")
            create_pw_dialog()
        else:
            encrypted_configuration = settings.get("Config")
            try:
                decrypted_configuration = decrypt(encrypted_configuration, password)
                undumped_configuration = json.loads(decrypted_configuration)
                for i in configuration.keys():
                    configuration[i] = undumped_configuration[i]
                show_options()
            except:
                create_pw_dialog()

def create_pw_dialog():
    dialog = ap.Dialog()
    dialog.title = "Enter Configuration Key"
    dialog.icon = ctx.icon
    dialog.add_text("Configuration Key").add_input(placeholder="Your configuration key", var="pw_var")
    dialog.add_button("Ok", callback = set_password)
    dialog.show()

def set_password(dialog : ap.Dialog):
    local_settings.set("encryption_password", dialog.get_value("pw_var"))
    get_settings()

def show_options():    
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
        dialog.add_button("Mount", callback=setup_mount)

        dialog.show()
    else:
        path = settings.get("mount_path")
        if path ==  "":
            path = os.path.normpath("/Volumes")

        dialog.add_text("Drive Location:\t").add_input(path, browse=ap.BrowseType.Folder, var = path_var)
        dialog.add_button("Mount", callback=setup_mount)
        dialog.show()

def isWin():
    if platform.system() == "Windows":
        return True
    return False

ctx.run_async(rclone_install.check_winfsp_and_rclone, get_settings)
