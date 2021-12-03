import os
from datetime import date
from enum import Enum

class VariableType(Enum):
    NAME = 1
    DATE = 2
    USER = 3
    INCREMENT = 4

def get_next_increment(template, current_folder):
    increment = 10
    leading_zeros = 4
    directories = [item for item in os.listdir(current_folder) if os.path.isdir(os.path.join(current_folder,item))]

    while True:
        name = template.replace("$", str(increment).zfill(leading_zeros), 1)
        pos_var = name.find("$")
        substr = name if pos_var == -1 else name[:pos_var]

        if not any(substr in dir for dir in directories):
            return str(increment).zfill(leading_zeros)

        increment = increment + 10

def resolve_variable(name, variable_type, current_folder, var_name="default", var_username="john doe"):
    replacement = ""
    if variable_type == VariableType.NAME:
        replacement = var_name
    elif variable_type == VariableType.DATE:
        replacement = date.today().strftime("%y%m%d")
    elif variable_type == VariableType.USER:
        initials = var_username.split(" ")
        for initial in initials:
            replacement = replacement + initial[0].upper()
    elif variable_type == VariableType.INCREMENT:
        replacement = get_next_increment(name, current_folder)

    return replacement

def remove_gitkeep(folder):
    for root, _, files in os.walk(folder):
        for file in files:
            if file == ".gitkeep":
                os.remove(os.path.join(root, file))
