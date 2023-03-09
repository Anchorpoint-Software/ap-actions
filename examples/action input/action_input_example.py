import anchorpoint as ap
import apsync as aps

ctx = ap.get_context()
ui = ap.UI()

# Access the YAML inputs through the context inputs dict
if "some_hardcoded_variable" in ctx.inputs:
    print("some_hardcoded_variable: " + ctx.inputs["some_hardcoded_variable"])

if "ask_the_user_variable" in ctx.inputs:
    print("ask_the_user_variable: " + ctx.inputs["ask_the_user_variable"])

if "ask_the_user_once_variable" in ctx.inputs:
    print("ask_the_user_once_variable: " + ctx.inputs["ask_the_user_once_variable"])

ui.show_console()
