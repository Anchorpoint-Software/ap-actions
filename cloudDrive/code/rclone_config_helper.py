
configuration = {
    "type": "",

    #S3 AWS
    "s3aws_access_key_id": "",
    "s3aws_secret_access_key": "",
    "s3aws_region": "",
    "s3aws_location_constraint": "",
    "s3aws_root_folder":"",

    #S3 Wasabi
    "s3wasabi_access_key_id": "",
    "s3wasabi_secret_access_key": "",
    "s3wasabi_region": "",
    "s3wasabi_root_folder":"",

    #Backblaze
    "b2_account": "",
    "b2_key":"",
    "b2_bucket_name": "",

    #Azure
    "azureblob_sas_url" :"",
    "azureblob_container_path" :""
}
remote_options = ["B2 (Backblaze)\t","S3 (AWS)\t","S3 (Wasabi)\t", "Azure Blob Storage\t"]

def get_config():
    return configuration

def get_remote_options():
    return remote_options

def get_config_type(value):
    if(value == remote_options[0]):
        return "b2"
    if(value == remote_options[1]):
        return "s3aws"
    if(value == remote_options[2]):
        return "s3wasabi"
    if(value == remote_options[3]):
        return "azureblob"
    return ""

def get_dropdown_label(config_type):
    if(config_type == "b2"):
        return remote_options[0]
    if(config_type == "s3aws"):
        return remote_options[1]
    if(config_type == "s3wasabi"):
        return remote_options[2]
    if(config_type == "azureblob"):
        return remote_options[3]
    return remote_options[0]