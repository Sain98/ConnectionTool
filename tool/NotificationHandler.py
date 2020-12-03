from plyer import notification as notify

def notification(old_status, new_status, server):
    notify.notify(
        title=f"{server} - Status change!",
        message=f"Old status: {old_status} | New status: {new_status}",
        app_name="ConnectionTool"
    )
