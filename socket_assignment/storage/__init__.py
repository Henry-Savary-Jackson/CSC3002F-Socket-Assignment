from socket_assignment import   users
import socket_assignment
import os
import json
import base64
from copy import deepcopy
import nacl
from uuid import uuid4

USERS_PATH = "users.json"
CHATS_PATH = "group_chats.json"
MEDIA_PATH = "media.json"
PRIVATE_KEY_PATH = "privkey.bin"

json_settings = {"indent":4}


def convert_message_for_storage(message):
    message = deepcopy(message) 
    if "data" in message and type(message["data"]) == bytes:
        message["data"] = base64.b64encode(message["data"]).decode()
    return message

def find_chat_with_name(name, chats):
    for chat_id in chats:
        if "name" not in chats[chat_id]:
            continue
        if chats[chat_id]["name"] == name:
            return chat_id

def add_new_media(server_name, data, filename, mimetype, media ):
    media_id = str(uuid4())
    media[media_id] = {"data":base64.b64encode(data).decode(), "filename":filename, "mimetype":mimetype }
    store_media(server_name,media)
    return media_id

def delete_connection(conn_id, connections, users):
    user_id = connections[conn_id]["user_id"]
    connections.pop(conn_id) 
    users.pop(user_id)

def store_signing_key(signing_key:nacl.signing.SigningKey, path):
    with open(path, "wb") as privkeyfile:
        privkeyfile.write(signing_key.encode())

def load_sign_verify_key(path):
    with open(path, "rb") as priv_key_file:
        privkey_bytes = priv_key_file.read()
        signing_key = nacl.signing.SigningKey(privkey_bytes)
        return signing_key, signing_key.verify_key


def store_media(server_name,media):
    dump_to_json_file(media, f"{server_name}-{MEDIA_PATH}")

def store_groups(server_name,groups):
    groups = deepcopy(groups) 
    for group_id in groups:
        group = groups[group_id]
        if "members" in group:
            group["members"] = list(group["members"]) 

    dump_to_json_file(groups,f"{server_name}-{CHATS_PATH}")
    
def dump_to_json_file(obj, path):
    with open(path, "w") as file_descriptor:
        try :
            json.dump( obj, file_descriptor, **json_settings)
        except Exception as e:
            file_descriptor.write("{}")
            print(f"Error writing to file {e}")

def load_from_json_file( path):
    if not os.path.exists(path):
        return dict()
    with open(path, "r") as file_descriptor:
        return json.load(file_descriptor)



def store_message_in_chat(chat_id,new_message,group_chats):
    new_message = convert_message_for_storage(new_message) 
    client_chat = group_chats[chat_id] if chat_id in group_chats else None
    if not client_chat:
        client_chat = {"chat_id":chat_id, "messages": []}
        group_chats[chat_id] = client_chat
    client_chat["messages"].append(new_message)


def load_users(server_name):
    return load_from_json_file(f"{server_name}-{USERS_PATH}")

def load_groups(server_name):
    groups =  load_from_json_file(f"{server_name}-{CHATS_PATH}")
    for group_id in groups:
        group = groups[group_id]
        if "members" in  group:
            group["members"] = set(group["members"])
    return groups

def load_media(server_name):
    return load_from_json_file(f"{server_name}-{MEDIA_PATH}")

def store_users(current_username,users):
    users = deepcopy(users)
    for username in users:
        user = users[username]
        "ip" in user and user.pop("ip")
        "port" in user and user.pop("port")
        "udp_port" in user and user.pop("udp_port")
        "connection_id" in user and user.pop("connection_id")

    dump_to_json_file(users, f"{current_username}-{USERS_PATH}")
    

