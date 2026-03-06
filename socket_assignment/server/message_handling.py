
from socket_assignment.utils.net import close, async_udp_client
import base64
import socket_assignment
from socket_assignment import connections ,  unacked_messages
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message
from socket_assignment.client.client_sending import send_message, send_message_udp, send_message_to_user
from socket_assignment.utils.protocol import AUTH_TOKEN_HEADER_NAME

from socket_assignment.storage import add_new_media, store_message_in_chat, store_groups

def check_message_is_reply(conn ,message):
    """This function will check if this message is being awaited by another task as a response.
    This is done by checking the "reply_to" header, containing the message_id of the message being replied to.
    If it is a reply, set the result of the corresponding future that is waiting for this message

    Will return True if it is a reply, in which case message handler tasks should ignore this message
    Otherwise, treat it as a novel message.
    """
    command = message["command"]
    message_id = message["message_id"]
    reply_to_id = message["headers"]["reply_to"] if "reply_to" in message["headers"] else None
    if reply_to_id and reply_to_id in unacked_messages:
        # if this message is a response to a message, then set result 
        # of the future and don't bother handling. the calling function 
        # of the original request should handle it by awaiting the future 
        future = unacked_messages[reply_to_id]["future"]
        future.set_result(message)
        unacked_messages.pop(reply_to_id)
        return True

    return False


# TODO: remove this soon, there is little need for auth tokens
def check_if_token_is_valid(conn_id, message, user_id):
    """Checks if the user has included the correct authentication token in a message."""
    headers = message["headers"]
    conn_info = connections[conn_id]
    assert "token" in conn_info
    true_token = conn_info["token"] 
    if  AUTH_TOKEN_HEADER_NAME not in headers or not headers[AUTH_TOKEN_HEADER_NAME]:
        raise ServerError(conn_info["connection"], message, "Missing authentication token!")

    msg_token = headers[AUTH_TOKEN_HEADER_NAME]
    if msg_token != true_token:
        raise ServerError(conn_info["connection"], message, "Wrong authentication token!")

async def handle_download_server(conn_id,message):
    users = socket_assignment.users
    media = socket_assignment.media

    conn = connections[conn_id]["connection"]

    headers = message["headers"]
    if "media_id" not in headers:
        raise ServerError(conn, message, "Must specify media_id to download!")

    media_id = headers["media_id"]
    if media_id not in media:
        raise ServerError(conn, message, "Media doesn't exist.")
    file_data = base64.b64decode(media[media_id]["data"].encode())
    response =  create_download_response_tcp(message, media[media_id]) 
    await send_message(conn, response, awaitable=False)

async def handle_chat_message_server(server_name,conn_id ,message, group_chats):
    users = socket_assignment.users
    media = socket_assignment.media

    conn_info = connections[conn_id]
    conn = conn_info["connection"]
     #check if chat_id is specified
    headers = message["headers"]
    if "chat_id" not in headers:
        raise ServerError(conn, message, "chat_id is not specified!")
    if "sender" not in headers: 
        raise ServerError(conn, message, "Missing sender header!")

    # remove the authentication token the client sent
    headers.pop(AUTH_TOKEN_HEADER_NAME)

    group_id = headers["chat_id"]
    if group_id not in group_chats:
        raise ServerError(conn, message, f"Group with id {group_id} doesn't exist!")
    sender = headers["sender"]
    if sender not in users:
        raise ServerError(conn, message, f"User {sender} doesn't exist!")

    mimetype = headers["mimetype"]
    if mimetype != "text/plain":
        if "filename" not in headers:
            raise ServerError(conn, message, "Missing filename header")
        filename = headers["filename"]
        media_id = add_new_media(server_name,message["data"], filename, mimetype, media)
        message["data"] = media_id.encode()
        headers["content_length"] = len(message["data"])
    #send message to all members in the group except the sender

    store_message_in_chat(group_id, message, group_chats)
    store_groups(server_name,group_chats)

    for user in group_chats[group_id]["members"]:
        if user != sender:
            #check if user is online
            await send_message_to_user(server_name,user,message, awaitable=False)
    
    await send_message(conn, create_ack_message(message), awaitable=False)