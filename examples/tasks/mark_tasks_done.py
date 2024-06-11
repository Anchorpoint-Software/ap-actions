import anchorpoint as ap
import apsync as aps

if __name__ == "__main__":
    ctx = ap.get_context()
    api = ap.get_api()

    # Iterate over all selected tasks
    for task in ctx.selected_tasks:
        # Retrieve a task by id
        task = api.tasks.get_task_by_id(task.id)

        # And update its status
        api.attributes.set_attribute_value(
            task, "Status", aps.AttributeTag("Done", "green")
        )

    ui = ap.UI()
    ui.show_success("Tasks Updated")
