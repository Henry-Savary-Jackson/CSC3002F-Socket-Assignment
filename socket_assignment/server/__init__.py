from email.mime import message

from socket_assignment.utils.net import close
from socket_assignment import connections , users
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message
from socket_assignment.client import send_message
from socket_assignment import media


VALID_COMMANDS_SERVER = ["CONNECT", "AUTHENTICATE", "ACK", "MESSAGE", "DOWNLOAD", "SESSION"]
VALID_COMMANDS_PEER = [""]

MAX_CONNECTIONS = 100

group_chats = dict()

async def handle_download_server(conn,message):
    headers = message["headers"]
    if "media_id" not in headers:
        raise ServerError(conn, message, "Must specify media_id to download!")

    media_id = headers["media_id"]
    if "stream" in headers and headers["stream"]:
        # TODO: handle streaming
        await send_message(conn, create_ack_message(message),awaitable=False)
    else:
        if media_id not in media:
            raise ServerError(conn, message, "Media doesn't exist.")
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
