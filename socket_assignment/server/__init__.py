from socket_assignment.utils.net import close, async_udp_client
from socket_assignment import connections , users
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message
from socket_assignment.client import send_message, send_message_udp
from socket_assignment.utils.protocol import AUTH_TOKEN_HEADER_NAME
from socket_assignment import media


MAX_CONNECTIONS = 100

group_chats = dict()

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

async def handle_download_server(conn,message):
    headers = message["headers"]
    if "media_id" not in headers:
        raise ServerError(conn, message, "Must specify media_id to download!")

    media_id = headers["media_id"]
    if media_id not in media:
        raise ServerError(conn, message, "Media doesn't exist.")
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
        file_data = media[media_id]["data"]
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


async def handle_chat_message_server(conn ,message):
    #check if chat_id is specified
    if "chat_id" not in message["headers"]:
        raise ServerError(conn, message, "Chat id is not specified.")
    group_id = message["headers"]["chat_id"]
    sender = message["headers"]["sender"]
    #send message to all members in the group except the sender
    for user in group_chats[group_id]["members"]:
        if user != sender:
            #check if user is online
            if "connection_id" in users[user]:
                conn_id = users[user]["connection_id"]
                await send_message(connections[conn_id]["connection"], message, awaitable=False)
            else:
                #user is offline, store message for later delivery
                if "pending_messages" not in users[user]:
                    users[user]["pending_messages"] = []
                users[user]["pending_messages"].append(message)

async def disconnect_server(conn_id):
    connection_info = connections[conn_id]
    socket = connection_info["connection"]
    user_id = connection_info["user_id"] if "user_id" in connection_info else None
    if user_id:
        users[user_id].pop("connection_id")
    connections.pop(conn_id)
    close(socket)


async def send_pending_messages(user_id):

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
        message = pending_messages.pop(0)
        await send_message(conn, message, awaitable=False) 
