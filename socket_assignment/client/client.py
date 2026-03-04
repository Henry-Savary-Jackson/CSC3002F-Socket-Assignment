import asyncio

import socket
from pathlib import Path
from socket_assignment.peer import  peer_tcp_port
from uuid import uuid4
import asyncio
from socket_assignment.peer.peer import run_peer, bind_peer_socket
from socket_assignment.client import pending_invites,  client_username, server_connection  , udp_socket, udp_port, client_chats, client_signing_key, client_verifier_key
import base64
from socket_assignment.utils.net import send, recv_message
import nacl
from mimetypes import guess_type
from socket_assignment import users, connections,unacked_messages
from socket_assignment.utils.protocol import create_download_message_tcp,create_reject_message,create_join_message,parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message, create_invite_message
from socket_assignment.utils.exceptions import server_exceptions_handled, ServerError
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment.peer import peer_tcp_port
from socket_assignment.peer.peer import listen_peer , create_peer_socket_client
from socket_assignment.security.auth import generate_keypair, authenticate_flow_client, connect_to_peer
from socket_assignment.server.message_handling import check_message_is_reply
from socket_assignment.storage import store_message_in_chat, delete_connection
from socket_assignment.client.client_sending import send_message , send_session
from socket_assignment.utils.exceptions import  server_exceptions_handled 
from socket_assignment.utils.net import create_socket, connect, recv_message, close, bind_udp_port,bind_server
from socket_assignment.utils.protocol import create_newchat_message,create_message,create_chat_message, create_direct_message, create_authentication_message, AUTH_TOKEN_HEADER_NAME

def ask_for_message(dest_id):
    type_msg = input("(F)ile/(T)ext:\n").upper()[:1]
    if (type_msg == "F"):
        path = input("Path:\n")
        with open(path, "rb") as fd:
            filename = Path(path).name
            data = fd.read()
            mimetype = guess_type(path)[0]
            return (data, mimetype, filename )
    elif type_msg == "T":
        text = input("Write your text message:\n")
        mimetype = "text/plain"
        return ( text.encode(), mimetype, None )
            

@server_exceptions_handled
async def handle_message_as_client(conn_id, message):
    conn_info = connections[conn_id]
    conn = conn_info["connection"] 

    cmd = message["command"]
    headers = message["headers"]

    if "sender" not in headers:
        raise ServerError(conn, message, "Missing sender header.")
    sender = headers["sender"]
    if cmd == "MESSAGE":
        if "chat_id" not in headers:
            raise ServerError(conn, message, "chat_id is missing")
        chat_id = headers["chat_id"] 
        store_message_in_chat(chat_id, message, client_chats) 
        mimetype = headers["mimetype"]
        if mimetype == "text/plain":
            # normal text message            
            print(f"\nNew message from {send}! : \n{message["data"].decode()}\n")
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
        print(f"\nUser  {message["headers"]["sender"]} joined chat {message["headers"]["chat_id"]}!")
    elif cmd == "REJECT":
        print(f"\nUser {message["headers"]["sender"]} rejected chat invite {message["headers"]["chat_id"]}!")


async def command_loop(conn_id, username):
    conn_info  = connections[conn_id]
    conn = conn_info["connection"]

    try :
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

                msg = create_invite_message(username, target, chat_id, connections[conn_id]["token"])
                resp = await send_message(conn, msg)
                if resp["command"] == "ACK":
                    print(f"Invite sent to {target} for chat {chat_id}")
                else:
                    print(f"Error: {resp["headers"]["cause"]}")
            elif parts[0] == "/invites":
                if pending_invites:
                    latest = pending_invites.pop()
                    chat_id = latest["headers"]["chat_id"]
                    inviter = latest["headers"]["sender"]
                    print(f"new pending invite to {chat_id} from {latest["headers"]["sender"]}")
                    decision = input("(A)ccept/(R)eject?\n").upper()[:1]
                    if decision == "A":
                        msg = create_join_message(latest, username, inviter,chat_id, conn_info["token"])
                        response = await send_message(conn,msg)
                        if response["command"] == "ACK":
                            client_chats[chat_id] =  {"messages":[]}
                            print(f"Joined chat {chat_id}")
                        else:
                            print("Join failed")
                    else:
                        msg = create_reject_message(latest, username, inviter,chat_id, conn_info["token"])
                        await send_message(conn, msg, awaitable=False)
                        print(f"Rejected invite for chat {chat_id}")

                else:
                    print("No pending invites,")
                    continue 
            elif parts[0] == "/msg":
                if len(parts) != 2:
                    print("Usage: /msg <chat_id> ")
                    continue
                chat_id = parts[1]
                data, mimetype, filename = ask_for_message(chat_id)
                msg = create_chat_message(username, chat_id, data, mimetype, conn_info["token"], filename=filename)
                await send_message(conn, msg,awaitable=False)

            elif parts[0] == "/dmsg":
                if len(parts) < 2:
                    print("Usage: /dmsg <user_id> ")
                    continue
                other = parts[1]
                if "connection_id" not in users[other]:
                    print("No peer connection set up!")
                    continue
                other_conn_id = users[other]["connection_id"]
                other_conn_info = connections[other_conn_id]
                other_conn = other_conn_info["connection"] 
                data, mimetype, filename = ask_for_message(other)

                client_token = other_conn_info["token"]

                msg = create_direct_message(username, other , data, mimetype, client_token, filename=filename)
                resp = await send_message(other_conn, msg)
                if resp["command"] == "ACK":
                    print("\nSucessfully received!\n")
                else:
                    print(f"\nError:{resp["headers"]["cause"]}\n")

            elif parts[0] == "/peer":
                if len(parts) < 2:
                    print("Usage: /peer <user_id> ")
                    continue
                target = parts[1]

                if target not in users:
                    ip,port, pubkey = await send_session(target)
                    if not ip :
                        continue

                target_conn_id = create_peer_socket_client(target)

                target_info = users[target]
                client_sock = connections[target_conn_id]["connection"]

                global client_signing_key
                global client_verifier_key

                asyncio.create_task(listen_peer(target_conn_id))


                result =  await connect_to_peer(target, client_username, client_signing_key, client_verifier_key,peer_tcp_port,udp_port)
                if not result:
                    print("\nError, could not connect to peer!")
                    delete_connection(target_conn_id)
                print(f"\nConnected to {target}!")

            elif parts[0] == "/create":
                if len(parts) < 2:
                    print("Usage: /create <chat_name> ")
                    continue
            
                chat_name = parts[1]
                msg = create_newchat_message(username,chat_name,conn_info["token"]  ) 
                response = await send_message(conn, msg)
                if response["command"] == "ACK":
                    print("Succesfully created")
                    
                    resp_headers = response["headers"]
                    chat_id = resp_headers["chat_id"]
                    print(chat_id)
                    client_chats[chat_id] = {"messages":[]}
                else: 

                    print("Error", response["headers"]["cause"])

            elif parts[0] == "/quit":
                msg = create_message("DISCONNECT", headers={"sender": username})
                await send_message(conn, msg, awaitable=False)
                break
            else:
                print("Unknown command")

    except asyncio.CancelledError :
        print("Cancelling!")

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
        conn.close()

async def run_client():
    server_host = "localhost"
    server_port = 5000
    username = input("Enter your username: ")
    global client_username
    client_username = username

    global client_signing_key
    global client_verifier_key
    client_signing_key, client_verifier_key = generate_keypair()
    sock = socket.socket()
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    try :
        await loop.sock_connect(sock, (server_host, server_port))
        print(f"\nConnected to server {server_host}:{server_port}")

        server_conn_id = "server"

        connections[server_conn_id] = {"connection":sock }

        listener_task = asyncio.create_task(client_listener(server_conn_id))

        udp_port = bind_udp_port(udp_socket)
        global peer_tcp_port

        print("Starting peer server")
        peer_socket = bind_peer_socket()
        peer_tcp_port = peer_socket.getsockname()[1]
        asyncio.create_task(run_peer(peer_socket))
        print("done")

        success = await authenticate_flow_client(server_conn_id, username, client_signing_key, client_verifier_key, peer_tcp_port, udp_port)
        if success:
            await command_loop(server_conn_id, username)

        

        close(sock)
        listener_task.cancel()
        print("\nDisconnected")
    except ConnectionRefusedError as cre:
        print("Failed to connect to server!")


