from socket_assignment.utils.net import close, async_udp_client
import base64
from socket_assignment import connections , users
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message, AUTH_TOKEN_HEADER_NAME
from socket_assignment.client.client_sending import send_message, send_message_udp
from socket_assignment.utils.net import create_socket
from socket_assignment import media


MAX_CONNECTIONS = 100

group_chats = dict()

server_sock = create_socket()

async def disconnect_server(conn_id):
    connection_info = connections[conn_id]
    socket = connection_info["connection"]
    user_id = connection_info["user_id"] if "user_id" in connection_info else None
    if user_id:
        users[user_id].pop("connection_id")
    connections.pop(conn_id)
    close(socket)


 
