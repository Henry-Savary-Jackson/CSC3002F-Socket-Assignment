from socket_assignment.utils.net import close, async_udp_client
import asyncio
import base64
import socket_assignment
from socket_assignment import connections
from socket_assignment.utils.exceptions import ServerError
from socket_assignment.utils.protocol import create_download_response_tcp, create_ack_message
from socket_assignment.client.client_sending import send_message, send_message_udp
from socket_assignment.utils.net import create_socket
from socket_assignment import media

MAX_CONNECTIONS = 100

server_sock = create_socket()
SERVER_PORT = 5000

def disconnect_server(conn_id):
    users = socket_assignment.users

    connection_info = connections[conn_id]
    socket = connection_info["connection"]
    user_id = connection_info["user_id"] if "user_id" in connection_info else None
    if user_id and "connection_id" in users[user_id]:
        task  = list(filter(lambda t: t.get_name()==f"{user_id}-online", asyncio.all_tasks()))
        if task:
            task[0].cancel()
        users[user_id].pop("connection_id")
    connections.pop(conn_id)
    close(socket)


 
