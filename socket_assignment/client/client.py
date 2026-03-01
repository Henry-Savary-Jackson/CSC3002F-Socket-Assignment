import asyncio

import socket
import uuid
import asyncio
from socket_assignment.client import  send_message,client_username, server_connection  
from socket_assignment.utils.net import send, recv_message
import nacl
from socket_assignment import users, connections,unacked_messages
from socket_assignment.server import VALID_COMMANDS_PEER
from socket_assignment.utils.protocol import create_join_message,parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment.client import send_message
from socket_assignment.utils.net import create_socket, connect, recv_message, close
from socket_assignment.utils.protocol import create_message, create_authentication_message

def generate_keypair():
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    return signing_key, verify_key


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

        future = unacked_messages[reply_to_id]["future"]
        future.set_result(message)
        del unacked_messages[message_id]

async def authenticate(conn, username, signing_key, verify_key):
    public_key_b64 = verify_key.encode(encoder=nacl.encoding.Base64Encoder).decode()
    connect_msg = create_message("CONNECT", headers={
        "sender": username,
        "public_key": public_key_b64,
        "ip": "127.0.0.1",
        "port": "0",
        "udp_port": "1"
    })
    challenge_msg = await send_message(conn, connect_msg, awaitable=True)
    if challenge_msg["command"] != "CHALLENGE":
        print("Expected CHALLENGE, got", challenge_msg["command"])
        return False
    challenge_data = challenge_msg["data"]
    signature = signing_key.sign(challenge_data)
    auth_msg = create_message("AUTHENTICATE", headers={"sender": username},
                              data=signature, reply=challenge_msg["message_id"])
    ack = await send_message(conn, auth_msg, awaitable=True)
    if ack["command"] == "ACK":
        print("Authentication successful")
        return True
    else:
        print("Authentication failed")
        return False

async def command_loop(conn, username):
    while True:
        cmd = await asyncio.get_event_loop().run_in_executor(None, input, "Enter command: ")
        parts = cmd.split()
        if not parts:
            continue
        if parts[0] == "/invite":
            if len(parts) < 3:
                print("Usage: /invite <target> <chat_id>")
                continue
            target, chat_id = parts[1], parts[2]
            msg = create_message("INVITE", headers={
                "sender": username,
                "target": target,
                "chat_id": chat_id
            })
            await send_message(conn, msg, awaitable=False)
            print(f"Invite sent to {target} for chat {chat_id}")
        elif parts[0] == "/join":
            if len(parts) < 2:
                print("Usage: /join <chat_id>")
                continue
            chat_id = parts[1]
            msg = create_message("JOIN", headers={
                "sender": username,
                "chat_id": chat_id
            })
            future = await send_message(conn, msg, awaitable=True)
            response = await future
            if response["command"] == "ACK":
                print(f"Joined chat {chat_id}")
            else:
                print("Join failed")
        elif parts[0] == "/reject":
            if len(parts) < 3:
                print("Usage: /reject <chat_id> <inviter>")
                continue
            chat_id, inviter = parts[1], parts[2]
            msg = create_message("REJECT", headers={
                "sender": username,
                "chat_id": chat_id,
                "inviter": inviter
            })
            await send_message(conn, msg, awaitable=False)
            print(f"Rejected invite for chat {chat_id}")
        elif parts[0] == "/quit":
            msg = create_message("DISCONNECT", headers={"sender": username})
            await send_message(conn, msg, awaitable=False)
            break
        else:
            print("Unknown command")

# handle connection 
async def client_listener(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    try:
        async for message in recv_message(conn):
            try :
                await handle_message_as_client(conn, message)
            except Exception as e:
                print(e)
    except ConnectionError as e:
      print(f"Error:{e}") 
    except BlockingIOError as be:
      print(f"Blocking Error:{be}")
    finally:
      print(f"Done with {conn.getsockname()}")
      conn.close()

async def main():
    server_host = "localhost"
    server_port = 5000
    username = input("Enter your username: ")
    signing_key, verify_key = generate_keypair()
    sock = socket.socket()
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    await loop.sock_connect(sock, (server_host, server_port))
    print(f"Connected to server {server_host}:{server_port}")

    success = await authenticate(sock, username, signing_key, verify_key)
    if not success:
        close(sock)
 
    listener_task = asyncio.create_task(client_listener(conn_id))
    await command_loop(sock, username)

    listener_task.cancel()
    close(sock)
    print("Disconnected")


