from socket_assignment import media
import json
import base64
import nacl
from uuid import uuid4

USERS_PATH = "users.json"
CHATS_PATH = "group_chats.json"
MEDIA_PATH = "media.json"
PRIVATE_KEY_PATH = "privkey.bin"
CLIENT_CHATS_PATH = ".json"

def add_new_media( data, filename, mimetype ):
    media_id = str(uuid4())
    media[media_id] = {"data":base64.b64encode(data), "filename":filename, "mimetype":mimetype }
    return media_id


def store_client_messages(messages):
    pass

def store_signing_key(signing_key:nacl.signing.SigningKey):
    with open(PRIVATE_KEY_PATH, "wb") as privkeyfile:
        privkeyfile.write(signing_key.encode())

def load_sign_verify_key():
    with open(PRIVATE_KEY_PATH, "rb") as priv_key_file:
        privkey_bytes = priv_key_file.read()
        signing_key = nacl.signing.SigningKey(privkey_bytes)
        return privkey_bytes, signing_key.verify_key.encode()
        
        

def store_users(users):
    users = users.copy()
    for user in users:
        user.pop("ip")
        user.pop("port")
        user.pop("udp_port")
        user.pop("connection_id")
