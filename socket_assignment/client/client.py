import asyncio

import socket
from pathlib import Path
from uuid import uuid4
import asyncio
from socket_assignment.peer.peer import run_peer, bind_peer_socket
from socket_assignment.client import pending_invites,  client_username, server_connection  , udp_socket, udp_port, client_signing_key, client_verifier_key
import base64
from socket_assignment.utils.net import send, recv_message
import nacl
from mimetypes import guess_type
import socket_assignment
from socket_assignment import connections
from socket_assignment.utils.protocol import create_download_message_tcp,create_reject_message,create_join_message,parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message, create_invite_message
from socket_assignment.utils.exceptions import server_exceptions_handled, ServerError
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment.peer.peer import listen_peer , create_peer_socket_client
from socket_assignment.security.auth import generate_keypair, authenticate_flow_client
from socket_assignment.server.message_handling import check_message_is_reply, send_message_to_user
from socket_assignment.storage import load_groups, load_media, load_users,store_message_in_chat, delete_connection, store_signing_key, load_sign_verify_key, find_chat_with_name
from socket_assignment.client.client_sending import send_message , send_session, send_pending_messages
from socket_assignment.utils.exceptions import  server_exceptions_handled 
from socket_assignment.utils.net import create_socket, connect, recv_message, close, bind_udp_port,bind_server
from socket_assignment.storage import store_groups, store_users
from socket_assignment.utils.protocol import create_newchat_message,create_message,create_chat_message, create_direct_message, create_authentication_message, AUTH_TOKEN_HEADER_NAME


async def get_input_async(*args):
    "Get input from the command line without blocking asyncio's event loop."
    return await asyncio.get_event_loop().run_in_executor(None, input, *args)

async def ask_for_message(dest_id):
    "GeT input from the command line to get the data for a text message."
    type_msg = (await get_input_async("(F)ile/(T)ext:\n")).upper()[:1]
    if (type_msg == "F"):
        path = await get_input_async("Path:\n")
        with open(path, "rb") as fd:
            filename = Path(path).name
            data = fd.read()
            mimetype = guess_type(path)[0]
            return (data, mimetype, filename )
    elif type_msg == "T":
        text = await get_input_async("Write your text message:\n")
        mimetype = "text/plain"
        return ( text.encode(), mimetype, None )
            

@server_exceptions_handled
async def handle_message_as_client(conn_id, message):
    group_chats = socket_assignment.group_chats
    users = socket_assignment.users
    client_username = socket_assignment.client.client_username
    

    conn_info = connections[conn_id]
    conn = conn_info["connection"] 

    cmd = message["command"]
    headers = message["headers"]

    if cmd == "MESSAGE":
        sender = headers["sender"]
        if "sender" not in headers:
            raise ServerError(conn, message, "Missing sender header.")
        if "chat_id" not in headers:
            raise ServerError(conn, message, "chat_id is missing")
        chat_id = headers["chat_id"] 
        store_message_in_chat(chat_id, message, group_chats) 
        store_groups(client_username, group_chats)
        mimetype = headers["mimetype"]
        if mimetype == "text/plain":
            # normal text message            
            print(f"\nNew message from {sender}! : \n{message["data"].decode()}\n")
        else:
            media_id = message["data"].decode()
            sender = headers["sender"]
            print(f"\nGot media from {sender}, (media-id: {media_id})\n")
            print("Downloading...\n")
            # download the media
            download_msg = create_download_message_tcp(message, media_id, conn_info["token"] )
            response= await send_message(conn, download_msg)
            if response["command"] == "ACK":
                data = response["data"]
                # show first 300 bytes of data
                print(f"Got data!:{data[:min(len(data),300)]}")
            else:
                # ERROR!! show cause
               print(response["headers"]["cause"]) 
            
    elif cmd == "INVITE":
        headers = message["headers"]
        sender = headers["sender"]
        chat_id = headers["chat_id"]
        print(f"\nNew invite to chat {chat_id} from {sender}!")
        pending_invites.append(message)
    elif cmd == "JOIN":
        sender = headers["sender"]
        chat_id = headers["chat_id"]
        print(f"\nUser {sender} joined chat {chat_id}!")
        if "members" in chat_id:
            group_chats[chat_id]["members"].add(sender)
        store_groups(client_username, group_chats)
    elif cmd == "REJECT":
        print(f"\nUser {message["headers"]["sender"]} rejected chat invite {message["headers"]["chat_id"]}!")


async def command_loop(conn_id, username):
    users = socket_assignment.users
    group_chats = socket_assignment.group_chats
    peer_tcp_port = socket_assignment.peer.peer_tcp_port
    udp_port = socket_assignment.client.udp_port
    client_signing_key = socket_assignment.client.client_signing_key
    client_verifier_key = socket_assignment.client.client_verifier_key


    conn_info  = connections[conn_id]
    conn = conn_info["connection"]
    loop = asyncio.get_event_loop()

    help_msg = """
    Commands:
        -/create <chat_name>
            Create a new group chat.
        -/invite <target> <chat_name>
            Invite a user to a chat.
        -/invites  
            Check on your latest invites to group chats to accept or reject.
        -/msg <chat_name>
            Send a message to the particular chat.
        -/dmsg <username>
            Send a direct message to a user via a peer to peer connection.
        -/peer <username>
            Initiate a peer-to-peer connection to the given user.
        -/chats 
            List all the group chats you are in.
        -/quit
            Disconnect from the server
        -/help 
            Print help message
    """

    print(help_msg)

    try :
        while True:
            cmd = await get_input_async("Enter command: ")
            parts = cmd.split()
            if not parts:
                continue
            if parts[0] == "/invite":
                if len(parts) < 3:
                    print("Usage: /invite <target> <chat_name>")
                    continue
                target, chat_name = parts[1], parts[2]
                chat_id = find_chat_with_name(chat_name, group_chats)
                if not chat_id:
                    print(f"No such chat with name {chat_name} was found.")
                    continue

                msg = create_invite_message(username, target, chat_id,chat_name, connections[conn_id]["token"])
                resp = await send_message(conn, msg)
                if resp["command"] == "ACK":
                    print(f"Invite sent to {target} for chat {chat_id}")
                else:
                    print(f"Error: {resp["headers"]["cause"]}")
            elif parts[0] == "/invites":
                if pending_invites:
                    latest = pending_invites.pop()
                    latest_headers = latest["headers"]
                    chat_id = latest_headers["chat_id"]
                    inviter = latest_headers["sender"]
                    chat_name = latest_headers["chat_name"]
                    print(f"New pending invite to  chat \"{chat_name}\" from {inviter}.")
                    decision = (await get_input_async("(A)ccept/(R)eject?\n")).upper()[:1]
                    if decision == "A":
                        msg = create_join_message(latest, username, inviter,chat_id, conn_info["token"])
                        response = await send_message(conn,msg)
                        if response["command"] == "ACK":
                            group_chats[chat_id] =  {"messages":[], "name":chat_name, "members": set()  }
                            store_groups(client_username,group_chats)
                            print(f"\nJoined chat {chat_id}")
                        else:
                            print("\nJoin failed")
                    else:
                        msg = create_reject_message(latest, username, inviter,chat_id, conn_info["token"])
                        await send_message(conn, msg, awaitable=False)
                        print(f"Rejected invite for chat {chat_id}")

                else:
                    print("No pending invites,")
                    continue 
            elif parts[0] == "/msg":
                if len(parts) != 2:
                    print("Usage: /msg <chat_name> ")
                    continue
                chat_name = parts[1]
                chat_id = find_chat_with_name(chat_name, group_chats)
                data, mimetype, filename = await ask_for_message(chat_id)
                msg = create_chat_message(username, chat_id, data, mimetype, conn_info["token"], filename=filename)
                response = await send_message(conn, msg)
                if response["command"] == "ACK":
                    print("Successfully sent")
                else:
                    print(f"Error {response["headers"]["cause"]}")

            elif parts[0] == "/dmsg":
                if len(parts) < 2:
                    print("Usage: /dmsg <user_id> ")
                    continue
                other = parts[1]
                if other not in users:
                    print("No peer connection was set up!")
                    continue

                data, mimetype, filename = await ask_for_message(other)

                msg = create_direct_message(username, other , data, mimetype, "", filename=filename)
                resp = await send_message_to_user(username,other, msg, awaitable=True) # make this ture in order to get a response
                if resp is None:
                    print("User is offline, sent into pending messages.")
                    continue 
                if resp["command"] == "ACK":
                    print("\nSucessfully received!\n")
                else:
                    print(f"\nError:{resp["headers"]["cause"]}\n")

            elif parts[0] == "/peer":
                if len(parts) < 2:
                    print("Usage: /peer <user_id> ")
                    continue
                target = parts[1]

                if target not in users or "ip" not in users[target] or "port" not in users[target]:
                    ip,port, pubkey = await send_session(target, username)
                    store_users(username, users)
                    if not ip  or not port or not pubkey:
                        print(f"User {target} doesn't exsit!")
                        continue

                target_conn_id = create_peer_socket_client(target)

                target_info = users[target]
                client_sock = connections[target_conn_id]["connection"]


                assert "ip" in target_info 
                assert "port" in target_info 

                ip = target_info["ip"] 
                tcp_port = target_info["port"]

                await connect(client_sock, ip,tcp_port)

                asyncio.create_task(listen_peer(username,target_conn_id))

                result = await authenticate_flow_client(target_conn_id, username,client_signing_key, client_verifier_key, peer_tcp_port, udp_port )
                if not result:
                    print("\nError, could not connect to peer!")
                    delete_connection(target_conn_id, connections, users)
                
                target_info["connection_id"] = target_conn_id 
                connections[target_conn_id]["user_id"] = target
                 
                await send_pending_messages(username, target)

                print(f"\nConnected to {target}\n!")

            elif parts[0] == "/create":
                if len(parts) < 2:
                    print("Usage: /create <chat_name> ")
                    continue
            
                chat_name = parts[1]
                msg = create_newchat_message(username,chat_name,conn_info["token"]  ) 
                response = await send_message(conn, msg)
                resp_headers = response["headers"]
                if response["command"] == "ACK":
                    print("Succesfully created")
                    
                    chat_id = resp_headers["chat_id"]
                    group_chats[chat_id] = {"name": chat_name,"messages":[], "members":set([username])}
                    store_groups(username, group_chats)
                else: 
                    print("Error", resp_headers["cause"])

            elif parts[0] == "/quit":
                msg = create_message("DISCONNECT", headers={"sender": username})
                await send_message(conn, msg, awaitable=False)
                break
            elif parts[0] == "/chats":
                print(*[group["name"] for group in group_chats.values() if "name" in group] ,sep="\n")
            elif parts[0] == "/help":
                print(help_msg)
            else:
                print("Unknown command")

    except (asyncio.CancelledError, EOFError):
        print("\nClosing program...") 

# handle connection 
async def client_listener(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    try:
        async for message in recv_message(conn):
            try :
                if check_message_is_reply(conn, message):
                    continue 
                asyncio.create_task(handle_message_as_client(conn_id, message))
                
            except Exception as e:
                print(e)
    except ConnectionError as e:
        print(f"\nError:{e}") 
    except BlockingIOError as be:
        print(f"\nBlocking Error:{be}")
    finally:
        print("\nDisconnected to server!")
        close(conn)
        

async def run_client():
    server_host = "127.0.0.1"
    server_port = 5000
    username = input("Enter your username: ")

    socket_assignment.client_username = username
    users = socket_assignment.users
     

    new = input("New account (Y/n)?\n").upper()[:1]
    if new == "Y":
        client_signing_key, client_verifier_key = generate_keypair()
        private_key_path = input("Give path to store private key:\n")
        store_signing_key(client_signing_key, private_key_path)

    else:
        private_key_path = input("Give the path to private key:\n")
        client_signing_key, client_verifier_key = load_sign_verify_key(private_key_path)

    socket_assignment.client.client_signing_key = client_signing_key 
    socket_assignment.client.client_verifier_key = client_verifier_key


    sock = socket.socket()
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    try :
        await loop.sock_connect(sock, (server_host, server_port))
        print(f"\nConnected to server {server_host}:{server_port}")

        server_conn_id = "server"

        connections[server_conn_id] = {"connection":sock }

        listener_task = asyncio.create_task(client_listener(server_conn_id))

        socket_assignment.client.udp_port = bind_udp_port(udp_socket)
        udp_port = socket_assignment.client.udp_port

        socket_assignment.group_chats = load_groups(username)
        socket_assignment.users = load_users(username)
        socket_assignment.media = load_media(username)

        print("Starting peer server")
        peer_socket = bind_peer_socket()
        peer_tcp_port = socket_assignment.peer.peer_tcp_port

        asyncio.create_task(run_peer(username,peer_socket))

        success = await authenticate_flow_client(server_conn_id, username, client_signing_key,   client_verifier_key if new == "Y" else None, peer_tcp_port, udp_port)
        if success:
            await command_loop(server_conn_id, username)

        close(sock)
        listener_task.cancel()
        print("Disconnected")

    except ConnectionRefusedError as cre:
        print("Failed to connect to server!")


