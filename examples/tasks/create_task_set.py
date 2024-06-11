import anchorpoint as ap

if __name__ == "__main__":
    ctx = ap.get_context()
    api = ap.get_api()

    # Get task block
    task_block = api.tasks.get_task_list_by_id(ctx.block_id)

    # And create a few new tasks
    for i in range(5):
        task = api.tasks.create_task(task_block, f"Python Task {i}")

    ui = ap.UI()
    ui.show_success("Tasks Created")
