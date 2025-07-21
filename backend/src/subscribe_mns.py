from authentication import AppRestrictedAuth
from mns_service import mnsService

if __name__ == "__main__":
    auth = AppRestrictedAuth()  # Use appropriate params if needed
    mns = mnsService(authenticator=auth)
    result = mns.subscribeNotification()
    print("Subscription Result:", result)
