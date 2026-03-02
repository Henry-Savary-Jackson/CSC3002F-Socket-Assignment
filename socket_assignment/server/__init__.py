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
    pass
#add message to the group chat
#for each member in group send message if they are online send the message to them except the sender if not pend the message until they come online



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
