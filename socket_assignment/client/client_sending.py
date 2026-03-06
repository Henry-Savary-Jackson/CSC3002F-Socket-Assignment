
import asyncio

import socket
from pathlib import Path
from uuid import uuid4
import base64
import asyncio
from socket_assignment.client import   server_connection  , udp_socket, udp_port 
from socket_assignment.utils.net import send, recv_message
import nacl
from mimetypes import guess_type
import socket_assignment
from socket_assignment import  connections,unacked_messages
from socket_assignment.utils.protocol import create_session_message,create_join_message,parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message, create_invite_message
from socket_assignment.storage import  store_users, convert_message_for_storage
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment.utils.net import create_socket, connect, recv_message, close, bind_server
from socket_assignment.utils.protocol import create_message,create_chat_message, create_direct_message, create_authentication_message, AUTH_TOKEN_HEADER_NAME

async def send_pending_messages(current_username,user_id):
    users = socket_assignment.users
    "Send all the pendings messages, if any to a user once they have connected."
    user_info  = users[user_id]
    if "connection_id" not in user_info:
        return
    conn_id = user_info["connection_id"]
    if conn_id not in connections:
        return 
    assert "connection" in connections[conn_id]
    conn = connections[conn_id]["connection"]
    pending_messages  = user_info["pending_messages"] if "pending_messages" in user_info else []
    while pending_messages:
        # while there are still unsent messages,send the first one
        message = pending_messages.pop(0)
        # pending messages would store their data as str not bytes
        mimetype = message["headers"]["mimetype"] if "mimetype" in message["headers"] else None
        if mimetype and "data" in message and mimetype != "text/plain":
            message["data"] = base64.b64decode(message["data"].encode()) # if them essage is a file, decode the base64 string
        elif mimetype == "text/plain":
            message["data"] = message["data"].encode() # if the message is plain text , convert string ot utf-8 bytes
        await send_message(conn, message, awaitable=False)

    store_users(current_username, users)


async def send_message(conn ,message, awaitable=True):
    """Given a socket, send this message to this socket
    
    awaitable is used to indicate if you will call await on this function
    in order to await the response from the socket.
    If you are not waiting for a response from sending this message, set awaitable to False
    """
    future =  asyncio.get_event_loop().create_future() if awaitable else None

    # keep track of this message as not yet receiving a reply
    # schedule the sending of data to event-loop
    try :
        if awaitable:
            unacked_messages[message["message_id"]] = {"message":message, "future":future}
        await send(conn,message_to_bytes(message))
        if future:
            return await future
    except Exception:
        if awaitable:
            unacked_messages.pop(message["message_id"])
        raise  

    # this returns a future, so that the caller can await the response from the remote connection

async def send_message_udp(udp_sock, message, server_ip, server_port):
    "Send a message object via UDP to a given server ip adress and port"
    await asyncio.get_event_loop().sock_sendto(udp_sock, message_to_bytes(message), (server_ip, server_port))

# for each  user, store ip, addr, connection id, public_key
async def send_session(target, client_username):
    "Do the process of getting the information for the peer and store it in list of users"
    connection_info = connections["server"]
    users = socket_assignment.users
    token =connection_info["token"]

    message = create_session_message(target, client_username, token)

    response_message = await send_message(connection_info["connection"], message)
    if response_message["command"] != "ACK":
        print(f"Error:{response_message["headers"]["cause"]}")
        return None, None, None 

    # get the info from message body
    info = parse_headers(response_message["data"].decode().split())

    if target in users:
        # update this user with this information
        users[target].update(info)
    else:
        users[target] = info.copy()
        users[target]["pending_messages"] = []
    return info["ip"], info["port"], info["public_key"] 


async def send_message_to_user(server_name,user, message):
    users = socket_assignment.users
    "Will send a message object to a given user if they are online, or add to pending messages if they are offline."
    if "connection_id" in users[user]:
        conn_id = users[user]["connection_id"]
        return await send_message(connections[conn_id]["connection"], message, awaitable=False)
    else:
        #user is offline, store message for later delivery
        if "pending_messages" not in users[user]:
            users[user]["pending_messages"] = []
        message = message.copy()
        if "data" in message:
           message["data"] = message["data"].decode()
        users[user]["pending_messages"].append(convert_message_for_storage(message))
        store_users(server_name, users)

