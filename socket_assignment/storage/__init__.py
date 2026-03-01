from socket_assignment import media

import base64
from uuid import uuid4

def add_new_media( data, filename, mimetype ):
    media_id = str(uuid4())
    media[media_id] = {"data":base64.b64encode(data), "filename":filename, "mimetype":mimetype }
    return media_id