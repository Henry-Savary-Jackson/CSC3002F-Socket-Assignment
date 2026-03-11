import asyncio
from uuid import uuid4
import socket
import datetime
import socket_assignment
from socket_assignment import connections
from socket_assignment.server import   MAX_CONNECTIONS, disconnect_server
from socket_assignment.server.message_handling import handle_download_server, handle_chat_message_server
from socket_assignment.utils.net import create_socket, get_connections, send, recv_message, close, async_udp_client
from socket_assignment.utils.protocol import create_message, create_ack_message,encode_dict_in_header_fmt, create_error_message
from socket_assignment.security.auth import authentication_flow_server
from socket_assignment.utils.exceptions import server_exceptions_handled, ServerError
from socket_assignment.client.client_sending import send_message , send_message_to_user, send_pending_messages
from socket_assignment.server.message_handling import  check_message_is_reply 
from socket_assignment.storage import load_groups, load_media, load_users , store_groups



async def online_broadcaster(conn_id):
    users = socket_assignment.users
    conn_info = connections[conn_id]
    username = conn_info["user_id"]
    loop = asyncio.get_event_loop()
    socket = await async_udp_client()
    try :
        while True:
            for other_username in users:
                user = users[other_username]
                if  other_username !=  username and  "ip" in user and "udp_port" in user:
                    ip = user["ip"]
                    udp_port = user["udp_port"]

                    await loop.sock_sendto(socket, f"{username}:online:{int(datetime.datetime.now().timestamp())}".encode() , (ip, int(udp_port)))
            await asyncio.sleep(5)
    except asyncio.CancelledError as e:
        print("Cancelled udp broadcaster")