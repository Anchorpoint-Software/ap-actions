from shutil import copyfile
import anchorpoint as ap
import apsync as aps
import sys, os

NO_IGNORE = "No .gitignore"

def on_is_action_enabled(path: str, type: ap.Type, ctx: ap.Context) -> bool:
    try:
        sys.path.insert(0, os.path.split(__file__)[0])
        import is_git_repo as git
        return git.is_git_repo(path)
    except Exception as e:
        print(str(e))
    return False

def get_ignore_dir(yaml_dir: str):
    return os.path.join(yaml_dir, "gitignore templates")

def get_ignore_file(yaml_dir: str, name: str):
    return os.path.join(get_ignore_dir(yaml_dir), f"{name}.gitignore")

def add_git_ignore(template_name: str, path: str, yaml_dir: str):
    ignore_src = get_ignore_file(yaml_dir, template_name)
    if os.path.exists(ignore_src):
        ignore_target = os.path.join(path, ".gitignore")
        if os.path.exists(ignore_target):
            os.remove(ignore_target)
        
        copyfile(ignore_src, ignore_target)

def _add_git_ignore(path: str, yaml_dir: str, dialog: ap.Dialog):
    dropdown = dialog.get_value("dropdown")
    add_git_ignore(dropdown, path, yaml_dir)
    dialog.close()
    ap.UI().show_success("Ignore File Created")

icon_map = {"Godot":":icons/organizations-and-products/godotEngine.svg", 
            "Unity":":icons/organizations-and-products/unityEngine.svg", 
            "UnrealEngine":":icons/organizations-and-products/unrealEngine.svg"}

def get_ignore_file_dropdown_entries(yaml_dir):
    ignore_files_dir = get_ignore_dir(yaml_dir)

    dropdown_values = []
    
    for f in os.listdir(ignore_files_dir):
        if os.path.isfile(os.path.join(ignore_files_dir, f)):
            base_name, ext = os.path.splitext(f)
            if ext == '.gitignore':
                entry = ap.DropdownEntry()
                entry.name = base_name
                entry.icon = icon_map.get(base_name, ":icons/Misc/git.svg")
                dropdown_values.append(entry)

    return dropdown_values

def get_ignore_file_default(ignore_file_dropdown_entries, path: str):
    def type_exists(type: str):
        try:
            return any(file.endswith(type) for file in os.listdir(path))
        except:
            return False
        
    def dir_exists(dir: str):
        return os.path.isdir(os.path.join(path, dir))

    for ignore_file_Entry in ignore_file_dropdown_entries:
        if "Unreal" in ignore_file_Entry.name and type_exists(".uproject"): return ignore_file_Entry.name
        elif "Unity" in ignore_file_Entry.name and dir_exists("Assets/Scenes"): 
                return ignore_file_Entry.name
    return None    

if __name__ == "__main__":
    ctx = ap.get_context()
    ui = ap.UI()
    
    settings = aps.Settings("gitignore")

    dialog = ap.Dialog() 
    dialog.title = "Add Git Ignore File"
    dialog.icon = ctx.icon

    dropdown_values = get_ignore_file_dropdown_entries(ctx.yaml_dir)
    if len(dropdown_values) == 0:
        ui.show_info("No gitignore templates found")
        sys.exit(0)

    dropdown_default = get_ignore_file_default(dropdown_values, ctx.path)

    dialog.add_text("Template: ").add_dropdown(dropdown_values[0].name, dropdown_values, var="dropdown")
    dialog.add_info("Add a <b>gitignore</b> to your project to exclude certain files from being<br> committed to Git (e.g. Unreal Engine's build result).") 
    dialog.add_button("Create", callback=lambda d: _add_git_ignore(ctx.path, ctx.yaml_dir, d))
    dialog.show(settings)

    if dropdown_default:
        dialog.set_value("dropdown", dropdown_default)