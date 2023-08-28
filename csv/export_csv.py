import os 
import tempfile
import anchorpoint
import apsync
from pathlib import Path
from datetime import datetime

ctx = anchorpoint.get_context()

def format_data(input_data):
    # If input is a list, join its elements with a comma
    if isinstance(input_data, list):
        string_data = ','.join(input_data)
        return f'"{string_data}"'
    
    # If input is a string with spaces, wrap it in double quotes
    if isinstance(input_data, str) and ' ' in input_data:
        return f'"{input_data}"'
    
    if isinstance(input_data, bool):
        return str(input_data)
    
    if isinstance(input_data, int):
        return str(input_data)
    
    if isinstance(input_data, datetime):
        return str(input_data.strftime('%Y-%m-%d'))
    
    return input_data

def read_attributes(selection,output_filename):

    output = "Name,"

    #Get all attributes in the project (everything what is under "Recent Attributes")
    attributes = api.attributes.get_attributes()

    for attribute in attributes:
        output+=format_data(str(attribute.name).strip())+","
    output = output[:-1]+"\n"        

    for target in selection:
        if isinstance(target, apsync.Task):
            output+=target.name+","
        else:
            output+= str(Path(target).stem)+","
        for attribute in attributes:
            attribute_value = api.attributes.get_attribute_value(target,attribute.name)            
            if(attribute_value is None):
                output+=","
            else:
                output+=(format_data(attribute_value)+",")

        output = output[:-1]+"\n" 
        
    output = output[:-1]     
    table_to_csv(output,output_filename)


def table_to_csv(table_string, output_filename):
    # Split the table string into rows
    rows = table_string.strip().split('\n')
    
    # Handle the header row separately
    header = rows[0].split('\t')
    header_csv = ','.join(header)
    
    # Convert the remaining rows into CSV rows
    csv_rows = [header_csv]
    for row in rows[1:]:
        columns = row.split('\t')
        csv_row = ','.join([col for col in columns])
        csv_rows.append(csv_row)
    
    # Write the CSV rows to the file
    with open(output_filename, 'w') as csvfile:
        csvfile.write('\n'.join(csv_rows))

def create_temp_directory():
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    return temp_dir

def create_csv_files(folder,folders,files,tasks):
    # start progress
    progress = anchorpoint.Progress("Creating CSV files", "Processing", infinite=True)

    temp_dir = create_temp_directory()
    csv_folder_location = os.path.join(temp_dir,folder+"_folders.csv")
    csv_file_location = os.path.join(temp_dir,folder+"_files.csv")
    csv_task_location = os.path.join(temp_dir,folder+"_tasks.csv")
    csv_files=[]

    if folders:
        read_attributes(folders,csv_folder_location)
        csv_files.append(csv_folder_location)
    if files:
        read_attributes(files,csv_file_location)
        csv_files.append(csv_file_location)
    if tasks:
        read_attributes(tasks,csv_task_location)
        csv_files.append(csv_task_location)

    if not os.path.exists(csv_folder_location) and not os.path.exists(csv_file_location):
        ui.show_error("Cannot copy to clipboard","CSV file could not be generated")
    else:        
        anchorpoint.copy_files_to_clipboard(csv_files)
        ui.show_success("CSV files generated","Paste them wherever you like") 

    progress.finish()
    
api = anchorpoint.get_api()
ui = anchorpoint.UI()

#Get the current selection of files and folders
selected_files = ctx.selected_files
selected_folders = ctx.selected_folders
selected_tasks = ctx.selected_tasks

ctx.run_async(create_csv_files,ctx.folder,selected_folders,selected_files,selected_tasks)
