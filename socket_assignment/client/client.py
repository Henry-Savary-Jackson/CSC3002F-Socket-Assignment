import asyncio
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment import users, connections, unacked_messages
from socket_assignment.client import send_message
from socket_assignment.utils.net import create_socket, connect, recv_message, close
from socket_assignment.utils.protocol import create_message, create_authentication_message
from socket_assignment.client.client import client_listener

def generate_keypair():
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    return signing_key, verify_key

async def authenticate(conn, username, signing_key, verify_key):
    public_key_b64 = verify_key.encode(encoder=nacl.encoding.Base64Encoder).decode()
    connect_msg = create_message("CONNECT", headers={
        "sender": username,
        "public_key": public_key_b64,
        "ip": "127.0.0.1",
        "port": "0"
    })
    future = await send_message(conn, connect_msg, awaitable=True)
    challenge_msg = await future
    if challenge_msg["command"] != "CHALLENGE":
        print("Expected CHALLENGE, got", challenge_msg["command"])
        return False
    challenge_data = challenge_msg["data"]
    signature = signing_key.sign(challenge_data)
    auth_msg = create_message("AUTHENTICATE", headers={"sender": username},
                              data=signature, reply=challenge_msg["message_id"])
    future = await send_message(conn, auth_msg, awaitable=True)
    ack = await future
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

async def check_message_is_reply(conn, message):
    if "reply_to" in message["headers"]:
        # If this is a reply to a message we sent, we should have a future for it
        reply_id = message["headers"]["reply_to"]
        if reply_id in unacked_messages:
            unacked_messages[reply_id]["future"].set_result(message)
            del unacked_messages[reply_id]

async def main():
    server_host = "localhost"
    server_port = 5000
    username = input("Enter your username: ")
    signing_key, verify_key = generate_keypair()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    await loop.sock_connect(sock, (server_host, server_port))
    print(f"Connected to server {server_host}:{server_port}")

    success = await authenticate(sock, username, signing_key, verify_key)
    if not success:
        close(sock)
        return

    conn_id = str(uuid.uuid4())
    connections[conn_id] = {"connection": sock, "user_id": username}

    listener_task = asyncio.create_task(client_listener(conn_id))
    await command_loop(sock, username)

    listener_task.cancel()
    close(sock)
    print("Disconnected")

if __name__ == "__main__":
    asyncio.run(main())

