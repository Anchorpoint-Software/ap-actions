import anchorpoint as ap
import time

ctx = ap.get_context()

def long_running_function(run_for_seconds):
    # Update every 100ms just to see progress in the UI more frequent
    update_interval = run_for_seconds * 10 
    
    # Once a progress object is created, Anchorpoint starts to show a running Task in the UI.
    # The task disappears as soon as the progress object is destroyed or finish() is called manually.
    # When setting infinite=True the progress indicator will just spin as long as it is active.
    # When setting cancelable=True the user is able to cancel the action within the UI.
    progress = ap.Progress("Async Example", f"Running for {run_for_seconds} seconds...", infinite=False, cancelable=True)

    # Simulate a heavy workload by sleeping
    for i in range(update_interval):
        time.sleep(0.1)

        # Report the progress to Anchorpoint
        progress.report_progress((i + 1) / (update_interval))

        # You can update the progress text as well
        # progress.set_text("What is the answer to life, the universe, and everthing?")

        # React to cancellation
        if progress.canceled:
            return

# Run our long running function in a separate Thread by calling 'run_async'
# The syntax is run_async(function_name, parameter1, parameter2, ...)
ctx.run_async(long_running_function, 5)