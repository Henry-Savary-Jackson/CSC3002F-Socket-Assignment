
from socket_assignment.utils.net import close, async_udp_client
import base64
from socket_assignment import connections , users, unacked_messages
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message
from socket_assignment.client.client_sending import send_message, send_message_udp, send_message_to_user
from socket_assignment.utils.protocol import AUTH_TOKEN_HEADER_NAME
from socket_assignment import media
from socket_assignment.server import group_chats
from socket_assignment.storage import add_new_media

def check_message_is_reply(conn ,message):
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

def check_if_token_is_valid(conn_id, message, user_id):
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
    conn = connections[conn_id]["connection"]

    headers = message["headers"]
    if "media_id" not in headers:
        raise ServerError(conn, message, "Must specify media_id to download!")

    media_id = headers["media_id"]
    if media_id not in media:
        raise ServerError(conn, message, "Media doesn't exist.")
    file_data = base64.b64decode(media[media_id]["data"].encode())
    if "stream" in headers and headers["stream"]:
        # TODO: handle streaming
        # create ack messages for each chunk of data
        if "sender" not in headers:
            raise ServerError(conn, message, "Missing sender header in download request!")
        sender = headers["sender"]
        user_info = users[sender]
        assert "ip" in user_info
        ip = user_info["ip"] 
        assert "udp_port" in user_info
        udp_port = user_info["udp_port"]
        udp_sock = async_udp_client()
        index = 0
        chunk_num = 0 
        CHUNK_SIZE = 4096
        while index < len(file_data):
            chunk = file_data[index: min(index+CHUNK_SIZE, len(file_data))]
            index += CHUNK_SIZE 
            chunk_num +=  1
            ack_message = create_ack_message(message, headers={"chunk_no": chunk_num, "content_length":len(chunk)},data=chunk)
            await send_message_udp(udp_sock, ack_message, ip, udp_port)
    else:
        response =  create_download_response_tcp(message, media[media_id]) 
        await send_message(conn, response,awaitable=False)



async def handle_chat_message_server(conn_id ,message):
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
        media_id = add_new_media(message["data"], filename, mimetype)
        message["data"] = media_id.encode()
        headers["content_length"] = len(message["data"])
    #send message to all members in the group except the sender
    for user in group_chats[group_id]["members"]:
        if user != sender:
            #check if user is online
            await send_message_to_user(user,message)