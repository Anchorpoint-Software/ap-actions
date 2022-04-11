import apsync

######################################
# Create File / Folder from Template #
######################################

def resolve_tokens(tokens: dict[str, str], target_folder: str):
    """ In this function you can overwrite all the resolved tokens of a template based on your needs.
    This happens before the Dialog is shown to the user.
    
    Example:
        if "Client" in tokens:
            tokens["Client"] = "Anchorpoint"
    """
    pass

def file_from_template_created(path: str, source: str, tokens: dict[str, str]):
    """ This function is called when a file template has been used.
    You can freely modify documents here. How about setting an attribute?
    """
    pass

def folder_from_template_created(path: str, source: str, tokens: dict[str, str]):
    """ This function is called when a folder template has been used.
    You can freely modify documents here. How about setting an attribute?
    """
    pass

def project_from_template_created(path: str, source: str, tokens: dict[str, str], project: apsync.Project):
    """ This function is called when a project template has been used.
    You can freely modify documents here. How about setting an attribute?
    """
    pass


####################
# Save as Template #
####################

def file_template_saved(name: str, path: str):
    """ This function is called when the 'Save as Template' action has saved a file template.
    You can freely modify the template here (e.g. add tokens and rename things) 
    """
    pass

def folder_template_saved(name: str, path: str):
    """ This function is called when the 'Save as Template' action has saved a folder template.
    You can freely modify the template here (e.g. add tokens and rename things) 
    """
    pass