''' UTILS FOR API '''

import uuid

def generate_fullurl() -> str:
    ''' returns fullurl '''
    return f"urn:uuid:{uuid.uuid4()}"
