import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

api = aps.Api.instance()
ctx = ap.Context.instance()

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

msg = aps.IpcMessage()
msg.topic = "APUnreal"
msg.kind = "hello"
msg.header = {
    "task": "Thumbnail",
    "path": ctx.path,
    "output_path": os.path.join(desktop, "test.png")
    }

print(ctx.path)
aps.ipc_publish(msg)