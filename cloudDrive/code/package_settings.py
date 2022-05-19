import anchorpoint as ap
import apsync as aps
import json
import string
import random

ctx = ap.Context.instance()
ui = ap.UI()
settings = aps.SharedSettings(ctx.workspace_id, "AnchorpointCloudMount")

def install_modules():
    progress = ap.Progress("Loading Security Module",infinite = True)
    ui.show_info("Loading Security Module")  
    ctx.install("pycryptodome")
    ctx.install("keyring")
    ctx.install("pyperclip")
    progress.finish()
    init_dialog()
    
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
password = ""
dropdown_values = ["S3 (e.g. AWS)\t", "B2 (Backblaze)\t"]

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
    configuration["type"] = get_config_type(dialog.get_value("dropdown_var"))
    configuration["provider"] = dialog.get_value("provider_var")
    configuration["access_key_id"] = dialog.get_value("access_key_var")
    configuration["secret_access_key"] = dialog.get_value("secret_access_key_var")
    configuration["region"] = dialog.get_value("region_var")
    configuration["location_constraint"] = dialog.get_value("location_constraint_var")    
    configuration["root_folder"] = dialog.get_value("root_folder_var")  
    configuration["b2_account"] = dialog.get_value("b2_account_var")    
    configuration["b2_key"] = dialog.get_value("b2_app_key_var")   
    configuration["b2_bucket_name"] = dialog.get_value("b2_bucket_name_var")   
    return configuration

def apply_callback(dialog : ap.Dialog):   
    from Crypto.Random import get_random_bytes

    configuration = get_configuration(dialog)
    dumped_configuration = json.dumps(configuration)

    password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    salt = get_random_bytes(32)
    secret_key = generate_secret_key(password, salt)

    encrypted_configuration = encrypt(dumped_configuration, secret_key, salt)

    settings.set("Config",encrypted_configuration)
    settings.store()
    keyring.set_password("AnchorpointCloudMount", "encryption_password", password)  

    pc.copy(password)
    ui.show_success("Configuration Code copied to Clipboard")  
    dialog.close()

def copy_configuration_key(dialog : ap.Dialog):
    password = keyring.get_password("AnchorpointCloudMount", "encryption_password")
    pc.copy(str(password))
    ui.show_success("Configuration Code copied to Clipboard")  
    
def init_dialog():
    import keyring, pyperclip as pc 
    if settings.get("Config")=="":
        create_dialog()
    else:
        password = keyring.get_password("AnchorpointCloudMount", "encryption_password")
        if password == None:
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
    configuration["type"] = ""
    configuration["provider"] = ""
    configuration["access_key_id"] = ""
    configuration["secret_access_key"] = ""
    configuration["region"] = ""
    configuration["location_constraint"] = ""
    configuration["root_folder"] = ""
    configuration["b2_account"] = ""
    configuration["b2_key"] = ""
    configuration["b2_bucket_name"] = ""

    try:
        keyring.delete_password("AnchorpointCloudMount", "encryption_password")
    except:
        print("Key has been already deleted")
        
    settings.set("Config","")
    settings.store()
    create_dialog()

def clear_config(dialog : ap.Dialog):
    configuration["type"] = ""
    configuration["provider"] = ""
    configuration["access_key_id"] = ""
    configuration["secret_access_key"] = ""
    configuration["region"] = ""
    configuration["location_constraint"] = ""
    configuration["root_folder"] = ""
    configuration["b2_account"] = ""
    configuration["b2_key"] = ""
    configuration["b2_bucket_name"] = ""

    try:
        keyring.delete_password("AnchorpointCloudMount", "encryption_password")
    except:
        print("Key has been already deleted")

    settings.set("Config","")
    settings.store()
    ui.show_success("Configuration has been cleared")  
    dialog.close()

def set_password(dialog : ap.Dialog):
    keyring.set_password("AnchorpointCloudMount", "encryption_password", dialog.get_value("pw_var"))
    init_dialog()

def get_config_type(value):
    if(value == dropdown_values[0]):
        return "s3"
    if(value == dropdown_values[1]):
        return "b2"
    return ""

def create_dialog():

    def toggleOptions(dialog,value):
        if(value==dropdown_values[0]):
            dialog.hide_row("b2_account_var",True)
            dialog.hide_row("b2_app_key_var",True)
            dialog.hide_row("b2_bucket_name_var",True)

            dialog.hide_row("provider_var",False)
            dialog.hide_row("access_key_var",False)
            dialog.hide_row("secret_access_key_var",False)
            dialog.hide_row("root_folder_var",False)

            dialog.hide_row("region_var",False)
            dialog.hide_row("location_constraint_var",False)

        else:
            dialog.hide_row("b2_account_var",False)
            dialog.hide_row("b2_app_key_var",False)
            dialog.hide_row("b2_bucket_name_var",False)

            dialog.hide_row("provider_var",True)
            dialog.hide_row("access_key_var",True)
            dialog.hide_row("secret_access_key_var",True)
            dialog.hide_row("root_folder_var",True)

            dialog.hide_row("region_var",True)
            dialog.hide_row("location_constraint_var",True)

        dialogSettings = aps.Settings()
        dialogSettings.set("dropdown_value",value)
        dialogSettings.store()
        

    # Create a dialog container
    dialog = ap.Dialog()
    dialog.title = "Cloud Drive Settings"
    if ctx.icon:
        dialog.icon = ctx.icon 

    dialogSettings = aps.Settings()
    current_dropdown = dialogSettings.get("dropdown_value",dropdown_values[0])

    dialog.add_text("Server\t            ").add_dropdown(current_dropdown, dropdown_values, var="dropdown_var",callback = toggleOptions)
    dialog.add_info("Choose an S3 compatible server such as AWS, MinIO and <br> Digital Ocean or choose a Backblaze B2 server.")

    dialog.add_text("Provider\t             ").add_input(configuration["provider"],placeholder="AWS", var="provider_var")

    #dialog.add_info("Set a location that your team can access, such as a folder in your Dropbox")

    dialog.add_text("Access Key\t             ").add_input(configuration["access_key_id"],placeholder="Get your access key from the IAM console",var="access_key_var")
    dialog.add_text("Secret Access Key  ").add_input(configuration["secret_access_key"],placeholder="Get your secret access key from the IAM console",var="secret_access_key_var")
    dialog.add_text("Bucket/ Folder Path").add_input(configuration["root_folder"],placeholder="bucketname/folder/subfolder",var="root_folder_var")
    dialog.add_text("Account Id\t             ").add_input(configuration["b2_account"],placeholder="Account Id or App Key Id",var="b2_account_var")
    dialog.add_text("App key\t             ").add_input(configuration["b2_key"],placeholder="Application Key",var="b2_app_key_var")
    dialog.add_text("Bucket Name           ").add_input(configuration["b2_bucket_name"],placeholder="File_Bucket",var="b2_bucket_name_var")
    dialog.add_info("You can get these keys from your service provider, such as <br> the IAM console at AWS.")

    dialog.add_text("Region\t             ").add_input(configuration["region"],placeholder="eu-central-1 (Optional)",var="region_var")
    dialog.add_text("Location Constraint").add_input(configuration["location_constraint"],placeholder="EU (Optional)",var="location_constraint_var")

    dialog.add_button("Copy Configuration Key", callback = copy_configuration_key, enabled = keyring.get_password("AnchorpointCloudMount", "encryption_password") != None).add_button("Clear Configuration", callback = clear_config)
    dialog.add_info("Your configuration is stored encrypted. The key allows any <br> of your team to mount a drive with this configuration.<br> Copy the key and share it with your team members.")
    dialog.add_button("Apply", callback = apply_callback)

    toggleOptions(dialog,current_dropdown)

    # Present the dialog to the user
    dialog.show()


try:
    import keyring, pyperclip as pc
    from Crypto.Cipher import AES
    init_dialog()
except:
    ctx.run_async(install_modules)
    