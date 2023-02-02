import anchorpoint as ap
import apsync as aps

ctx, api = ap.get_context()
ui = ap.UI()
print(ctx.path)
# To quickly create a task (and a task list) call 
task = api.tasks.create_task(ctx.path, "Todo List", "Create Rig")

# You can access a task list by name
tasklist = api.tasks.get_task_list(ctx.path, "Todo List")

# And get all tasks
all_tasks = api.tasks.get_tasks(tasklist)
for task in all_tasks:
    print(f"Task: {task.name}")

# Set a status on the task
api.attributes.set_attribute_value(task, "Status", aps.AttributeTag("Done", aps.TagColor.green))

ui.show_success("Tasks created")