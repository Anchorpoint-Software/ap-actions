from ast import arguments
from re import sub
import shutil
import zipfile
import anchorpoint as ap
import apsync as aps
import platform
import subprocess
import os
import io
import requests
import json
import tempfile

ctx = ap.Context.instance()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointCloudMount")
RCLONE_INSTALL_URL = "https://github.com/rclone/rclone/releases/download/v1.58.1/rclone-v1.58.1-windows-386.zip"

configuration = {
    "type": "",
    "provider": "",
    "access_key_id": "",
    "secret_access_key": "",
    "region": "",
    "location_constraint": "",
    "root_folder":"",
    "b2_account": "",
    "b2_key":"",
    "b2_bucket_name": ""
}

rclone_path = os.path.join(ctx.yaml_dir,"rclone.exe")

def install_modules():
    progress = ap.Progress("Loading Modules",infinite = True)
    ui.show_info("Loading Modules", description="This will only happen once")  
    ctx.install("pycryptodome")
    ctx.install("keyring")
    progress.finish()
    check_winfsp()

def check_rclone():
    if not os.path.isfile(rclone_path):
        # download zip
        progress = ap.Progress("Loading RClone", infinite = True)
        r = requests.get(RCLONE_INSTALL_URL)
                
        # open zip file and extract rclone.exe to the right folder
        z = zipfile.ZipFile(io.BytesIO(r.content))
        
        with z.open('rclone-v1.58.1-windows-386/rclone.exe') as source:
            with open(rclone_path, "wb") as target:
                shutil.copyfileobj(source, target)

        progress.finish()

def check_winfsp():
    winfsp_path = os.path.join(os.environ["ProgramFiles(x86)"],"WinFsp/bin/launcher-x64.exe")
    if os.path.isfile(winfsp_path):
        check_rclone()
        get_settings()
    else:
        progress = ap.Progress("Loading WinFsp",infinite = True)
        winget = subprocess.run(
            "winget install -e --id WinFsp.WinFsp --accept-source-agreements", capture_output=True
        )
        progress.finish()
        if winget.returncode != 0:
            print(winget.stderr)
            ui.show_error("Failed to install WinFsp", description="Google WinFsp and install it manually.")
        else:
            check_rclone()
            get_settings()

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
                    f"{configuration['provider']}",
                    "--s3-access-key-id",
                    f"{configuration['access_key_id']}",
                    "--s3-secret-access-key",
                    f"{configuration['secret_access_key']}"
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
            return f":s3{configuration['root_folder']}"
        if(configuration["type"]=="b2"):
            return f":b2:{configuration['b2_bucket_name']}"

    settings = aps.Settings()    
    cache_path = settings.get("cachepath",default=get_default_cache_path())

    drive = dialog.get_value("drive_var")

    if not os.path.isdir(cache_path):
        os.mkdir(cache_path)

    base_arguments = [
        rclone_path,      
        "mount"
    ]
    
    config_arguments = create_config_arguments()

    if(configuration["region"] and configuration["type"]=="s3"):
        config_arguments.append("--s3-region")  
        config_arguments.append(f"{configuration['region']}")
    if(configuration["location_constraint"] and configuration["type"]=="s3"):
        config_arguments.append("--s3-location-constraint")  
        config_arguments.append(f"{configuration['location_constraint']}")

    config_arguments.append(create_location_arguments())
    config_arguments.append(f"{drive}:")

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
    ]

    arguments = base_arguments + config_arguments + rclone_arguments

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
    #startupinfo.wShowWindow = subprocess.SW_HIDE     

    ctx.run_async(run_rclone, arguments, startupinfo)
    
    #create_bat_file("process "+f'{drive}: "'+f'{ctx.path}"',drive)
    dialog.close()

def run_rclone(arguments, startupinfo):
    rclone_success = "The service rclone has been started"
    
    p = subprocess.Popen(
        args=arguments,
        startupinfo=startupinfo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True)
      
    for line in p.stdout:
        myjson = is_json(line)

        if myjson != None and myjson["level"] == "error":
            ui.show_error("Mount Failed", str(p.stdout))
            return
        
        if rclone_success in line:
            ui.show_success("Mount Successful")
            return

def is_json(myjson):
    try:
        myjson = json.loads(myjson)
    except ValueError as e:
        return
    return myjson

def get_default_cache_path():
    app_data_roaming = os.getenv('APPDATA')
    app_data = os.path.abspath(os.path.join(app_data_roaming, os.pardir))
    return os.path.join(app_data,"Local/rclone").replace("/","\\")

def is_admin():
    return True

def get_settings():
    import keyring, pyperclip as pc 
    if settings.get("Config")=="":
        if is_admin:
            ui.show_info("No cloud drive configured", description="Please setup a cloud drive")
        else:
            ui.show_info("No cloud drive configured", description="Ask your workspace owner to setup a cloud drive")
    else:
        password = keyring.get_password("AnchorpointCloudMount", "encryption_password")
        if password == None:
            print("no pw")
            create_pw_dialog()
        else:
            encrypted_configuration = settings.get("Config")
            try:
                decrypted_configuration = decrypt(encrypted_configuration, password)
                undumped_configuration = json.loads(decrypted_configuration)

                configuration["type"] = undumped_configuration["type"]
                configuration["provider"] = undumped_configuration["provider"]
                configuration["access_key_id"] = undumped_configuration["access_key_id"]
                configuration["secret_access_key"] = undumped_configuration["secret_access_key"]
                configuration["region"] = undumped_configuration["region"]
                configuration["location_constraint"] = undumped_configuration ["location_constraint"]
                configuration["root_folder"] = undumped_configuration ["root_folder"]
                configuration["b2_account"] = undumped_configuration ["b2_account"]
                configuration["b2_key"] = undumped_configuration ["b2_key"]
                configuration["b2_bucket_name"] = undumped_configuration ["b2_bucket_name"]

                show_options()
            except: 
                create_pw_dialog()

def create_pw_dialog():
    dialog = ap.Dialog()
    dialog.title = "Enter Configuration Key"
    dialog.icon = "icons/driveCloud.svg"
    dialog.add_text("Configuration Key").add_input(placeholder="Your configuration key", var="pw_var")
    dialog.add_button("Ok", callback = set_password)
    dialog.show()

def set_password(dialog : ap.Dialog):
    keyring.set_password("AnchorpointCloudMount", "encryption_password", dialog.get_value("pw_var"))
    get_settings()

def show_options():    

    drives = get_unused_drives()

    if len(drives) == 0:
        ui.show_error("No drives to mount", "Unmount another drive first")
        return

    dialog = ap.Dialog()
    dialog.title = "Mount Cloud Drive"

    if ctx.icon:
        dialog.icon = ctx.icon    

    dialog.add_text("Drive Letter:\t").add_dropdown(drives[0], drives, var="drive_var")
    dialog.add_button("Mount", callback=setup_mount)

    dialog.show()

if platform.system() == "Darwin":
    ui.show_error("Unsupported Action", "This action is only supported on Windows :-(")
else:
    try:
        import keyring
        from Crypto.Cipher import AES        
        ctx.run_async(check_winfsp)        
    except:
        ctx.run_async(install_modules)  