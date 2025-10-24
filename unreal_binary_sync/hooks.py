import anchorpoint as ap
import apsync as aps
import sync_binaries


def on_event_received(id, payload, ctx: ap.Context):
    print(
        f"Received event with ID: {id} and payload: {payload} with context: {ctx}")

    if isinstance(payload, dict):
        payload = payload.get('type')

    if id == "gitpull" and payload == "success":
        sync_binaries.sync(ctx)
