
configuration = {
    "type": "",

    #S3
    "s3_provider": "",
    "s3_access_key_id": "",
    "s3_secret_access_key": "",
    "s3_region": "",
    "s3_location_constraint": "",
    "s3_endpoint": "",
    "s3_root_folder":"",

    #Backblaze
    "b2_account": "",
    "b2_key":"",
    "b2_bucket_name": "",

    #Azure
    "azureblob_sas_url" :"",
    "azureblob_container_path" :""
}
remote_options = ["B2 (Backblaze)\t","S3 (AWS, Wasabi)\t", "Azure Blob Storage\t"]

def get_config():
    return configuration

def get_remote_options():
    return remote_options

def get_config_type(value):
    if(value == remote_options[0]):
        return "b2"
    if(value == remote_options[1]):
        return "s3"
    if(value == remote_options[2]):
        return "azureblob"
    return ""

def get_dropdown_label(config_type):
    if(config_type == "b2"):
        return remote_options[0]
    if(config_type == "s3"):
        return remote_options[1]
    if(config_type == "azureblob"):
        return remote_options[2]
    return remote_options[0]