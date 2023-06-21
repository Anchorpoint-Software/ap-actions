import anchorpoint

ctx = anchorpoint.get_context()
api = anchorpoint.get_api()
ui = anchorpoint.UI()

#Get the current selection of files and folders
selected_files = ctx.selected_files
selected_folders = ctx.selected_folders

def read_attribute(path):
    #Get all attributes in the project (everything what is under "Recent Attributes")
    proj_attributes = api.attributes.get_attributes()
    #Collect the output in a string
    output = ""

    #Get the Attribute field of the file/folder
    for attribute in proj_attributes:
        atttribute_value = api.attributes.get_attribute_value(path,attribute.name)

        #If the Attribute field is not empty, add it to the output string. Add a linebreak at the end
        if(atttribute_value is not None):
            output += attribute.name + ": " + str(atttribute_value) +"<br>"

    #Show a toast in the UI
    ui.show_info("Attributes",output)


for f in selected_files:
    read_attribute(f)

for f in selected_folders:
    read_attribute(f)
