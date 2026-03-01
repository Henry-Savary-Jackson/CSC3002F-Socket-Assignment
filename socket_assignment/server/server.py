import asyncio
import socket
from socket_assignment import users, connections, unacked_messages
from socket_assignment.server import group_chats
from socket_assignment.utils.net import create_socket, get_connections, send, recv_message, close
from socket_assignment.utils.protocol import create_message, create_ack_message, create_error_message
from socket_assignment.security.auth import authentication_flow_server
from socket_assignment.utils.exceptions import server_excpetions_handled
from socket_assignment.client import send_message
from socket_assignment.client.client import check_message_is_reply

MAX_CONNECTIONS = 5
active_connections = 0

async def send_error(conn, original_msg, explanation):
    error_msg = create_error_message(original_msg, explanation)
    await send_message(conn, error_msg, awaitable=False)

@server_excpetions_handled
async def handle_message_main_server(conn, message):
    global active_connections
    if check_message_is_reply(conn, message):
        return

    command = message["command"]
    if command == "CONNECT":
        await authentication_flow_server(conn, message)
    elif command == "DOWNLOAD":
        # Placeholder – implement as needed
        pass
    elif command == "INVITE":
        headers = message.get("headers", {})
        target = headers.get("target")
        chat_id = headers.get("chat_id")
        sender = headers.get("sender")
        if not target or not chat_id or not sender:
            await send_error(conn, message, "Missing target, chat_id, or sender")
            return
        if target not in users:
            await send_error(conn, message, f"User {target} does not exist")
            return
        target_info = users[target]
        if "connection_id" not in target_info:
            await send_error(conn, message, f"User {target} is offline")
            return
        target_conn_id = target_info["connection_id"]
        target_conn = connections[target_conn_id]["connection"]
        invite_msg = create_message("INVITE", headers={
            "chat_id": chat_id,
            "sender": sender,
            "target": target
        }, reply=message["message_id"])
        await send_message(target_conn, invite_msg, awaitable=False)
        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)
    elif command == "JOIN":
        headers = message.get("headers", {})
        chat_id = headers.get("chat_id")
        username = headers.get("sender")
        if not chat_id or not username:
            await send_error(conn, message, "Missing chat_id or sender")
            return
        if chat_id not in group_chats:
            group_chats[chat_id] = {"members": set(), "creator": username}
        group_chats[chat_id]["members"].add(username)
        for member in group_chats[chat_id]["members"]:
            if member == username:
                continue
            if member in users and "connection_id" in users[member]:
                member_conn = connections[users[member]["connection_id"]]["connection"]
                notify = create_message("JOIN_NOTIFY", headers={
                    "chat_id": chat_id,
                    "new_member": username
                })
                await send_message(member_conn, notify, awaitable=False)
        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)
    elif command == "REJECT":
        headers = message.get("headers", {})
        chat_id = headers.get("chat_id")
        username = headers.get("sender")
        inviter = headers.get("inviter")
        if not chat_id or not username or not inviter:
            await send_error(conn, message, "Missing chat_id, sender, or inviter")
            return
        if inviter in users and "connection_id" in users[inviter]:
            inviter_conn = connections[users[inviter]["connection_id"]]["connection"]
            reject_msg = create_message("REJECT_NOTIFY", headers={
                "chat_id": chat_id,
                "user": username
            })
            await send_message(inviter_conn, reject_msg, awaitable=False)
        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)
    elif command == "DISCONNECT":
        for conn_id, info in list(connections.items()):
            if info.get("connection") is conn:
                user_id = info.get("user_id")
                if user_id and user_id in users:
                    users[user_id].pop("connection_id", None)
                del connections[conn_id]
                active_connections -= 1
                break
        close(conn)
    else:
        await send_error(conn, message, f"Unknown command {command}")

async def handle_new_conn(conn):
    global active_connections
    try:
        async for message in recv_message(conn):
            await handle_message_main_server(conn, message)
    except (ConnectionError, BlockingIOError) as e:
        print(f"Connection error: {e}")
    finally:
        print(f"Done with {conn.getsockname()}")
        for conn_id, info in list(connections.items()):
            if info.get("connection") is conn:
                user_id = info.get("user_id")
                if user_id and user_id in users:
                    users[user_id].pop("connection_id", None)
                del connections[conn_id]
                active_connections -= 1
                break
        close(conn)

async def run_server(host='localhost', port=5000):
    global active_connections
    sock = create_socket()
    sock.bind((host, port))
    sock.listen(100)
    sock.setblocking(False)
    print(f"Server listening on {host}:{port}")

    async for conn, addr in get_connections(sock):
        if active_connections >= MAX_CONNECTIONS:
            print(f"Rejected connection from {addr}: max connections reached")
            try:
                await asyncio.get_running_loop().sock_sendall(conn, b"Server full\n")
            except:
                pass
            close(conn)
            continue
        active_connections += 1
        print(f"New connection from {addr}, active: {active_connections}")
        asyncio.create_task(handle_new_conn(conn))

if __name__ == "__main__":
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    asyncio.run(run_server(port=port))