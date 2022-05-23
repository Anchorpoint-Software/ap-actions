import apsync as aps

aps.Api.configure_daemon("/Users/jochenhunz/Documents/Anchorpoint/development/anchorpoint_develop/TwainSolution/ap-web/ap-clientd/clientd", "127.0.0.1:57413")
api = aps.Api.instance()
api.set_client_name("client")

msg = aps.IpcMessage()
msg.topic = "PythonTest"
msg.kind = "hello"
msg.header = {"message": "Hello from Anchorpoint"}

aps.ipc_publish(msg)