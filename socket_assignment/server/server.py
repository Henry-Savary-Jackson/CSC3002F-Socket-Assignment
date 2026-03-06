import asyncio
from uuid import uuid4
import socket
import socket_assignment
from socket_assignment import connections
from socket_assignment.server import   MAX_CONNECTIONS, disconnect_server
from socket_assignment.server.message_handling import handle_download_server, handle_chat_message_server
from socket_assignment.utils.net import create_socket, get_connections, send, recv_message, close
from socket_assignment.utils.protocol import create_message, create_ack_message,encode_dict_in_header_fmt, create_error_message, AUTH_TOKEN_HEADER_NAME
from socket_assignment.security.auth import authentication_flow_server
from socket_assignment.utils.exceptions import server_exceptions_handled, ServerError
from socket_assignment.client.client_sending import send_message , send_message_to_user, send_pending_messages
from socket_assignment.server.message_handling import check_if_token_is_valid, check_message_is_reply 
from socket_assignment.storage import load_groups, load_media, load_users , store_groups


async def send_error(conn, original_msg, explanation):
    error_msg = create_error_message(original_msg, explanation)
    await send_message(conn, error_msg, awaitable=False)

@server_exceptions_handled
async def handle_message_main_server(server_name,conn_id, message):
    users = socket_assignment.users
    group_chats = socket_assignment.group_chats

    assert conn_id in connections


    conn = connections[conn_id]["connection"]
    if check_message_is_reply(conn, message):
        return

    command = message["command"]
    if command == "CONNECT":
        await authentication_flow_server("server",conn_id, message)
        if "user_id" in connections[conn_id]:
            user_id = connections[conn_id]["user_id"]
            await send_pending_messages(server_name,user_id)
    elif command == "DOWNLOAD":
        await handle_download_server(conn_id, message)
    elif command == "MESSAGE":
        await handle_chat_message_server(server_name,conn_id, message, group_chats)
    elif command == "INVITE":
        headers = message.get("headers", {})
        target = headers.get("target")
        chat_id = headers.get("chat_id")
        sender = headers.get("sender")
        headers.pop(AUTH_TOKEN_HEADER_NAME)

        if not target or not chat_id or not sender:
            raise ServerError(conn, message, "Missing target, chat_id, or sender!")
        if target not in users:
            raise ServerError(conn, message, f"User {target} does not exist!")
        if chat_id not in group_chats:
            raise ServerError(conn, message, f"Chat {chat_id} does not exist!")

        # send invite notification to target
        await send_message_to_user(server_name,target, message) 

        # acknowledge message to inviter
        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)

    elif command == "JOIN":
        headers = message.get("headers", {})
        chat_id = headers.get("chat_id")
        sender = headers.get("sender")
        inviter = headers.get("inviter")
        # get rid of authentication token
        headers.pop(AUTH_TOKEN_HEADER_NAME)

        if not chat_id or not sender or not inviter:
            raise ServerError(conn, message,"Missing chat_id or sender or inviter!" ) 
        if inviter not in users:
            raise ServerError(conn, message,f"Inviter user {inviter} doesn't exist!" ) 
        if chat_id not in group_chats:
            raise ServerError(conn, message,f"Group chat {chat_id} doesn't exist!" ) 
        

        # alert all members of group chat
        for member in group_chats[chat_id]["members"]:
            await send_message_to_user(server_name,member, message)

        # add to list of member
        group_chats[chat_id]["members"].add(sender)

        store_groups(server_name,group_chats)

        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)

    elif command == "REJECT":
        headers = message.get("headers", {})
        chat_id = headers.get("chat_id")
        sender = headers.get("sender")
        inviter = headers.get("inviter")
        headers.pop(AUTH_TOKEN_HEADER_NAME)
        if not chat_id or not sender or not inviter:
            raise ServerError(conn, message,"Missing chat_id, sender, or inviter!")
        if inviter not in users:
            raise ServerError(conn, message,f"Inviter user {inviter} doesn't exist!" ) 
        if chat_id not in group_chats:
            raise ServerError(conn, message,f"Group chat {chat_id} doesn't exist!" ) 

        # tell the inviter they rejected
        await send_message_to_user(server_name,inviter, message)

        # tell invitee that the message was acknowledged
        ack = create_ack_message(message)
        await send_message(conn, ack, awaitable=False)

    elif command == "DISCONNECT":
        disconnect_server(conn_id)
    elif command == "CREATE":
        chat_id = str(uuid4())
        headers = message["headers"]
        if "chat_name" not in headers:
            raise ServerError(conn, message, "No chat_name given!")

        chat_name = headers["chat_name"]
        sender = headers["sender"]
        # creagte new group chat
        group_chats[chat_id] = {"members":set([sender]), "creator":sender ,"name":chat_name, "messages":[]}
        store_groups(server_name,group_chats) 

        await send_message(conn, create_ack_message(message, headers={"chat_id":chat_id}), awaitable=False)
    elif command == "SESSION":
        headers = message["headers"]
        if "target" not in headers:
            raise ServerError(conn, message, "Missing target header!")
        target = headers["target"]
        if target not in users:
            raise ServerError(conn, message, f"User {target} doesn't exist!")
        target_info = users[target]
        if "connection_id" not in target_info:
            raise ServerError(conn, message, f"User {user} is offline.")
        properties = ["ip", "port", "udp_port", "public_key"] # properties to send the clinet regarding this target
        output_info = { prop:target_info[prop] for prop in properties }
        data = encode_dict_in_header_fmt(output_info).encode()
        ack_msg = create_ack_message(message, data=data)
        await send_message(conn, ack_msg, awaitable=False)
    else:
        raise ServerError(conn, message, f"Unknown command {command}.")

async def handle_new_conn(server_name,conn_id):
    assert conn_id in connections
    conn = connections[conn_id]["connection"]
    try:
        async for message in recv_message(conn):
            asyncio.create_task(handle_message_main_server(server_name,conn_id, message))
    except (ConnectionError, BlockingIOError) as e:
        print(f"Connection error: {e}")
    finally:
        conn_info = connections[conn_id]
        if "user_id" in conn_info:
            print(f"Done with {conn_info["user_id"]}\'s connection.")
        else :
            print(f"Done with {conn_id} connection.")
        disconnect_server(conn_id)


async def run_server(host='localhost', port=5000):

    server_name = "server"

    socket_assignment.users = load_users(server_name)
    socket_assignment.media = load_media(server_name)
    socket_assignment.group_chats = load_groups(server_name)
    

    sock = socket_assignment.server.server_sock 
    try :
        sock.bind((host, port))
        sock.listen(100)
        sock.setblocking(False)
        print(f"Server listening on {host}:{port}")

        async for conn, addr in get_connections(sock):
            if len(connections) >= MAX_CONNECTIONS:
                print(f"Rejected connection from {addr}: max connections reached")
                try:
                    await asyncio.get_event_loop().sock_sendall(conn, b"Server full\n")
                except:
                    pass
                close(conn)
                continue
            print(f"New connection from {addr}, active: {len(connections)}")
            conn_id = str(uuid4())
            connections[conn_id] = { "connection":conn} 
            asyncio.create_task(handle_new_conn(server_name,conn_id))
        
    except asyncio.CancelledError as e:
        print("cancelled")
    except Exception as e:
        print(e)
    except InterruptedError as e:
        print(e)
    finally:
        close(sock)

if __name__ == "__main__":
    import sys
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    asyncio.run(run_server(port=port))