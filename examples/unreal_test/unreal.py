import anchorpoint as ap
import apsync as aps
import os

ctx = ap.Context.instance()
ui = ap.UI()

api = aps.Api.instance()
ctx = ap.Context.instance()

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')

# use filename as thumbnail output name
path = ctx.path
temp = path.split("/")[-1]
file_name = temp.split(".")[0]

msg = aps.IpcMessage()
msg.topic = "APUnreal"
msg.kind = "hello"
msg.header = {
    "task": "Thumbnail",
    "path": path,
    "output_path": os.path.join(desktop, file_name+".png")
    }

print(ctx.path)
aps.ipc_publish(msg)