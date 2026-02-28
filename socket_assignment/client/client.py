import uuid
import asyncio
from socket_assignment.client import  client_username, connections, server_connection, sending_queue, unacked_messages
from socket_assignment.utils.net import send, recv_message
from socket import*
from socket_assignment import users
from socket_assignment.server import VALID_COMMANDS_PEER
from socket_assignment.utils.protocol import parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message

import asyncio
from socket import socket, AF_INET, SOCK_STREAM


async def async_tcp_client():
    server_name = "localhost"
    server_port = None
    loop = asyncio.get_running_loop()
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.setblocking(False)
    await loop.sock_connect(client_socket, (server_name, server_port))
    username = input("Insert your username: ")
    await loop.sock_sendall(client_socket, username.encode())
    data = await loop.sock_recv(client_socket, 1024)
    print("From Server:", data.decode())

    client_socket.close()



async def async_udp_client():
    server_name = "localhost"
    server_port = None

    loop = asyncio.get_running_loop()

    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.setblocking(False)

    username = input("Insert your username: ")
    await loop.sock_sendto(client_socket, username.encode(), (server_name, server_port))
    data, addr = await loop.sock_recvfrom(client_socket, 2048)
    print("From Server:", data.decode())
    client_socket.close()


def check_message_is_reply(conn ,message):
    command = message["command"]
    message_id = message["message_id"]
    reply_to_id = message["headers"]["reply_to"] if "reply_to" in message["headers"] else None
    if reply_to_id and reply_to_id in unacked_messages:
        # if this message is a response to a message, then set result 
        # of the future and don't bother handling. the calling function 
        # of the original request should handle it by awaiting the future 

        future = unacked_messages[message_id]["future"]
        future.set_result(message)
        del unacked_messages[message_id]
        return True

    return False


def handle_message_as_client(conn, message):
    if check_message_is_reply(conn, message):
        return

    command = message["command"]
    # only message a client socket cna receieve that isn't some reply is a notification of an invite

    if command == "INVITE":
        pass

# handle connection 
async def client_listener(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    try:
        async for message in recv_message:
            handle_message_as_client(conn, message)
    except ConnectionError as e:
      print(f"Error:{e}") 
    except BlockingIOError as be:
      print(f"Blocking Error:{be}")
    finally:
      print(f"Done with {conn.getsockname()}")
      conn.close()


