import anchorpoint as ap
import apsync as aps
import json
import string
import random

import rclone_config_helper as rclone_config

ctx = ap.Context.instance()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointCloudMount")
local_settings = aps.Settings("rclone")

password = ""
dropdown_values = rclone_config.get_remote_options()
configuration = rclone_config.get_config()

def create_dialog():

    def toggleOptions(dialog,value):
        for key in configuration.keys():
            row_var = f"{str(key)}_var"
            if str(key) != "type":
                hide = True
                if rclone_config.get_config_type(dialog.get_value("type_var")) in str(key):
                    hide = False
                dialog.hide_row(row_var,hide)
            

    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "Cloud Drive Settings"
    if ctx.icon:
        dialog.icon = ctx.icon 

    dialog.add_text("Server\t\t").add_dropdown(rclone_config.get_dropdown_label(configuration["type"]), dropdown_values, var="type_var",callback = toggleOptions)
    dialog.add_info("Choose an S3 compatible server such as AWS, Wasabi or choose <br>a Backblaze B2 server. Take a look at this <a href='https://docs.anchorpoint.app/docs/2-manage-files/2-Cloud-NAS/'>tutorial</a>.")

    #Backblaze
    dialog.add_text("Key Id\t\t").add_input(configuration["b2_account"],placeholder="039skN...",var="b2_account_var")
    dialog.add_text("Application Key\t").add_input(configuration["b2_key"],placeholder="ca6bfe00...",var="b2_key_var")
    dialog.add_text("Bucket/ Folder\t").add_input(configuration["b2_bucket_name"],placeholder="myBucket/myFolder...",var="b2_bucket_name_var")

    #S3 AWS
    dialog.add_text("Access Key\t\t").add_input(configuration["s3aws_access_key_id"],placeholder="XXXBTBISU...",var="s3aws_access_key_id_var")
    dialog.add_text("Secret Access Key\t").add_input(configuration["s3aws_secret_access_key"],placeholder="XXXO1jJ.../73Hu...",var="s3aws_secret_access_key_var")
    dialog.add_text("Region\t\t").add_input(configuration["s3aws_region"],placeholder="eu-central-1 (Optional)",var="s3aws_region_var")
    dialog.add_text("Location Constraint\t").add_input(configuration["s3aws_location_constraint"],placeholder="EU (Optional)",var="s3aws_location_constraint_var")
    dialog.add_text("Bucket/ Folder\t").add_input(configuration["s3aws_root_folder"],placeholder="myBucket/myFolder...",var="s3aws_root_folder_var")


    #s3 Wasabi
    dialog.add_text("Access Key\t\t").add_input(configuration["s3wasabi_access_key_id"],placeholder="XXXBTBISU...",var="s3wasabi_access_key_id_var")
    dialog.add_text("Secret Access Key\t").add_input(configuration["s3wasabi_secret_access_key"],placeholder="XXXO1jJ.../73Hu...",var="s3wasabi_secret_access_key_var")
    dialog.add_text("Region\t\t").add_input(configuration["s3wasabi_region"],placeholder="eu-central-1",var="s3wasabi_region_var")
    dialog.add_text("Bucket/ Folder\t").add_input(configuration["s3wasabi_root_folder"],placeholder="myBucket/myFolder...",var="s3wasabi_root_folder_var")

    #Azure
    dialog.add_text("Shared access signature").add_input(configuration["azureblob_sas_url"],placeholder="https://myazureaccount...",var="azureblob_sas_url_var")
    dialog.add_text("Container/ Folder\t").add_input(configuration["azureblob_container_path"],placeholder="myContainer/myFolder...",var="azureblob_container_path_var")

    dialog.add_button("Copy Configuration Key", callback = copy_configuration_key, enabled = local_settings.get("encryption_password") != "").add_button("Clear Configuration", callback = clear_config)
    dialog.add_info("Your configuration is stored encrypted. The key allows any <br> of your team to mount a drive with this configuration.<br> Copy the key and share it with your team members.")
    dialog.add_button("Apply", callback = apply_callback)

    toggleOptions(dialog,dropdown_values[0])

    # Present the dialog to the user
    dialog.show()

def is_optional(var):
    return var == "s3aws_region_var" or var == "s3aws_location_constraint_var"

def install_modules():
    progress = ap.Progress("Loading Security Module",infinite = True)
    ui.show_info("Loading Security Module")  
    ctx.install("pycryptodome")
    ctx.install("pyperclip")
    progress.finish()
    init_dialog()
    
def generate_secret_key(password: str, salt: bytes) -> str:
    from Crypto.Protocol.KDF import PBKDF2
    return PBKDF2(password, salt, dkLen=32)

def encrypt(data: str, secret_key: bytes, salt: bytes) -> str:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    cipher = AES.new(secret_key, AES.MODE_CBC) 
    ciphered_data = cipher.encrypt(pad(data.encode(), AES.block_size))
    
    return (cipher.iv + ciphered_data + salt).hex()

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

def get_configuration(dialog : ap.Dialog):
    configuration["type"] = rclone_config.get_config_type(dialog.get_value("type_var"))
    for i in configuration.keys():
        if i !="type" and configuration["type"] in str(i):
            configuration_val = str(dialog.get_value(f"{i}_var")).strip()
            #print (i,configuration_val,f"{i}_var")
            if configuration_val is not "":
                configuration[i] = configuration_val
            elif is_optional(f"{i}_var"): 
                configuration[i] = configuration_val
            else:
                return False
            optional_configuration_val = dialog.get_value(f"{i}_var_opt")
            if optional_configuration_val is not None:
                configuration[i] = str(optional_configuration_val).strip()
    return configuration

def apply_callback(dialog : ap.Dialog):   
    from Crypto.Random import get_random_bytes
    import pyperclip as pc 

    configuration = get_configuration(dialog)
    if(not configuration):
        ui.show_error("Configuration is incomplete","The cloud drive needs the necessary information to work properly")  
        return

    dumped_configuration = json.dumps(configuration)

    password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    salt = get_random_bytes(32)
    secret_key = generate_secret_key(password, salt)

    encrypted_configuration = encrypt(dumped_configuration, secret_key, salt)

    settings.set("Config",encrypted_configuration)
    settings.store()
    local_settings.set("encryption_password", password)
    local_settings.store()

    pc.copy(password)
    ui.show_success("Configuration Code copied to Clipboard")  
    dialog.close()

def copy_configuration_key(dialog : ap.Dialog):
    password = local_settings.get("encryption_password")
    pc.copy(str(password))
    ui.show_success("Configuration Code copied to Clipboard")  
    
def init_dialog():
    import pyperclip as pc 
    if settings.get("Config")=="":
        create_dialog()
    else:
        password = local_settings.get("encryption_password")
        if password == None:
            create_pw_dialog()
        else:
            encrypted_configuration = settings.get("Config")
            try:
                decrypted_configuration = decrypt(encrypted_configuration, password)
                undumped_configuration = json.loads(decrypted_configuration)
                 
                for i in configuration.keys():
                    configuration[i] = undumped_configuration[i]

                create_dialog()
            except: 
                create_pw_dialog()

        
def create_pw_dialog():
    dialog = ap.Dialog()
    dialog.title = "Settings Configuration Key"
    if ctx.icon:
        dialog.icon = ctx.icon 
    dialog.add_text("Configuration Key").add_input(placeholder="Your configuration key", var="pw_var")
    dialog.add_info("The password generated when saving your configuration. <br> If you can't find it anymore, create a new configuration.")
    dialog.add_button("Ok", callback = set_password).add_button("Clear Configuration", callback = enter_new_config)
    dialog.show()

def enter_new_config(dialog : ap.Dialog):
    #clears the dictionary
    for key in configuration: configuration[key] = ""

    try:
        local_settings.set("encryption_password", "")
        local_settings.store()
    except:
        print("Key has been already deleted")
        
    settings.set("Config","")
    settings.store()
    create_dialog()

def clear_config(dialog : ap.Dialog):
    #clears the dictionary
    for key in configuration: configuration[key] = ""

    try:
        local_settings.set("encryption_password", "")
        local_settings.store()
    except:
        print("Key has been already deleted")

    settings.set("Config","")
    settings.store()
    ui.show_success("Configuration has been cleared")  
    dialog.close()

def set_password(dialog : ap.Dialog):
    local_settings.set("encryption_password", dialog.get_value("pw_var"))
    local_settings.store()
    init_dialog()

try:
    import pyperclip as pc
    from Crypto.Cipher import AES
    init_dialog()
except:
    ctx.run_async(install_modules)
    