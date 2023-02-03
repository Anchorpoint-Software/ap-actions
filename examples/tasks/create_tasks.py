import anchorpoint as ap
import apsync as aps

ctx, api = ap.get_context()
ui = ap.UI()

# To quickly create a task (and a task list) call 
task = api.tasks.create_task(ctx.path, "Todo List", "Create Rig")

# You can access a task list by name
tasklist = api.tasks.get_task_list(ctx.path, "Todo List")

# And get all tasks
all_tasks = api.tasks.get_tasks(tasklist)
for task in all_tasks:
    print(f"Task: {task.name}")

# Set an icon for the task. To get the path of an icon right click the icon in the icon picker
api.tasks.set_task_icon(task, aps.Icon("qrc:/icons/multimedia/setting.svg", "blue"))

# Set a status on the task
api.attributes.set_attribute_value(task, "Status", aps.AttributeTag("Done", "green"))


ui.show_success("Tasks created")