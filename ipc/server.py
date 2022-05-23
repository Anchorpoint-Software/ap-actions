import apsync as aps
import time, sys

aps.Api.configure_daemon("/Users/jochenhunz/Documents/Anchorpoint/development/anchorpoint_develop/TwainSolution/ap-web/ap-clientd/clientd", "127.0.0.1:57413")
api = aps.Api.instance()
api.set_client_name("server")

sub = aps.ipc_subscribe("PythonTest")

def msg_hello(header: dict[str, str], body: str):
    print(msg.header, msg.body)

def msg_shutdown():
    sys.exit(0)

def handle_message(msg: aps.IpcMessage) -> bool:
    if msg.kind == "hello":
        msg_hello(msg.header, msg.body)
        return True
    if msg.kind == "shutdown":
        msg_shutdown()

    return False

print("Server Running")
while True:
    while sub.has_messages():
        msg = sub.get_message()
        if not handle_message(msg):
            print("Message unknown")

    time.sleep(0.5)

