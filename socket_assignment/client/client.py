import asyncio

import socket
from pathlib import Path
from socket_assignment.peer import  peer_tcp_port
from uuid import uuid4
import asyncio
from socket_assignment.client import pending_invites,  client_username, server_connection  , udp_socket, udp_port, client_chats, client_signing_key, client_verifier_key
from socket_assignment.utils.net import send, recv_message
import nacl
from mimetypes import guess_type
from socket_assignment import users, connections,unacked_messages
from socket_assignment.utils.protocol import create_reject_message,create_join_message,parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message, create_invite_message
from socket_assignment.utils.exceptions import server_exceptions_handled
import socket
import uuid
import nacl.signing
import nacl.encoding
from socket_assignment.peer import peer_tcp_port
from socket_assignment.peer.peer import listen_peer 
from socket_assignment.security.auth import generate_keypair, authenticate_flow_client, connect_to_peer
from socket_assignment.server.message_handling import check_message_is_reply
from socket_assignment.storage import store_message_in_chat
from socket_assignment.client.client_sending import send_message 
from socket_assignment.utils.exceptions import  server_exceptions_handled 
from socket_assignment.utils.net import create_socket, connect, recv_message, close, bind_server
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
    if cmd == "MESSAGE":
        if "chat_id" not in headers:
            raise ServerError(conn, message, "chat_id is missing")
        chat_id = headers["chat_id"] 
        store_message_in_chat(chat_id, message, client_chats) 
    elif cmd == "INVITE":
        print(f"New invite! {message["message_id"]}")
        pending_invites.append(message)
    elif cmd == "JOIN":
        print(f"User joined chat! {message["headers"]["sender"]}")
    elif cmd == "REJECT":
        print(f"User rejected! {message["headers"]["sender"]}")


async def command_loop(conn_id, username):
    conn_info  = connections[conn_id]
    conn = conn_info["connection"]

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

            msg = create_invite_message(username, target, chat_id, connections[conn_id]["client_token"])
            resp = await send_message(conn, msg)
            if resp["command"] == "ACK":
                print(f"Invite sent to {target} for chat {chat_id}")
            else:
                print(f"Error: {resp["headers"]["cause"]}")
        elif parts[0] == "/invites":
            # if len(parts) < 2:
            #     print("Usage: /join <chat_id>")
            #     continue
            if pending_invites:
                latest = pending_invites.pop()
                chat_id = latest["headers"]["chat_id"]
                print(f"new pending invite to {chat_id} from {latest["headers"]["sender"]}")
                decision = input("(A)ccept/(R)eject?\n").upper()[:1]
                if decision == "A":
                    msg = create_join_message(latest, username, chat_id, conn_info["client_token"])
                    response = await send_message(conn,msg)
                    if response["command"] == "ACK":
                        client_chats[chat_id] =  {"messages":[]}
                        print(f"Joined chat {chat_id}")
                    else:
                        print("Join failed")
                else:
                    msg = create_reject_message(latest, username, chat_id, conn_info["client_token"])
                    await send_message(conn, msg, awaitable=False)
                    print(f"Rejected invite for chat {chat_id}")

            else:
                print("No pending invites,")
                continue 
            
        # elif parts[0] == "/reject":
        #     if len(parts) < 3:
        #         print("Usage: /reject <chat_id> <inviter>")
        #         continue
        #     chat_id, inviter = parts[1], parts[2]
        #     msg = create_message("REJECT", headers={
        #         "sender": username,
        #         "chat_id": chat_id,
        #         "inviter": inviter
        #     })
        #     await send_message(conn, msg, awaitable=False)

        elif parts[0] == "/msg":
            if len(parts) != 2:
                print("Usage: /msg <chat_id> ")
                continue
            chat_id = parts[1]
            data, mimetype, filename = ask_for_message(chat_id)
            msg = create_chat_message(username, chat_id, data, mimetype, conn_info["client_token"], filename=filename)
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
            data, mimetype, filename = ask_for_message(chat_id)

            client_token = other_conn_info["client_token"]

            msg = create_direct_message(username, other , data, mimetype, client_token, filename=filename)
            resp = await send_message(conn, msg)
            if resp["command"] == "ACK":
                print("Sucessfully sent!")
            else:
                print(f"Error:{resp["headers"]["cause"]}")

        elif parts[0] == "/peer":
            if len(parts) < 2:
                print("Usage: /peer <user_id> ")
                continue
            user_id = parts[1]
            conn_id = await connect_to_peer(user_id, client_username, client_signing_key, client_verifier_key,peer_tcp_port,udp_port)
            if conn_id is None:
                print("Error, could not connect to peer!")
            asyncio.create_task(listen_peer(conn_id))
            print(f"Connected to {user_id}")

        elif parts[0] == "/create":
            if len(parts) < 2:
                print("Usage: /create <chat_name> ")
                continue
        
            chat_name = parts[1]
            msg = create_newchat_message(username,chat_name,conn_info["client_token"]  ) 
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
      print(f"Error:{e}") 
    except BlockingIOError as be:
      print(f"Blocking Error:{be}")
    finally:
      print(f"Done with {conn.getsockname()}")
      conn.close()

async def run_client():
    server_host = "localhost"
    server_port = 5000
    username = input("Enter your username: ")

    signing_key, verify_key = generate_keypair()
    sock = socket.socket()
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    await loop.sock_connect(sock, (server_host, server_port))
    print(f"Connected to server {server_host}:{server_port}")

    server_conn_id = "server"

    connections[server_conn_id] = {"connection":sock }

    listener_task = asyncio.create_task(client_listener(server_conn_id))

    print(udp_port)
    bind_server(udp_socket, udp_port)

    success = await authenticate_flow_client(server_conn_id, username, signing_key, verify_key, peer_tcp_port, udp_port)
    if success:
        await command_loop(server_conn_id, username)

    close(sock)
    listener_task.cancel()
    print("Disconnected")


