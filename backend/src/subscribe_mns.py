from authentication import AppRestrictedAuth
from mns_service import MnsService

if __name__ == "__main__":
    auth = AppRestrictedAuth()
    mns = MnsService(authenticator=auth)
    result = mns.subscribeNotification()
    print("Subscription Result:", result)
