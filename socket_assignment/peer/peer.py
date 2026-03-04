# code for starting the peer server
# randomly choose ip, port

import socket
import base64
from uuid import uuid4
import asyncio
import socket_assignment
from socket_assignment import connections
from socket_assignment.utils.exceptions import server_exceptions_handled, ServerError
from socket_assignment.storage import add_new_media, store_message_in_chat, store_groups
from socket_assignment.utils.net import create_socket ,get_connections, send, recvall, close, recv_message
from socket_assignment.client.client_sending import send_message,send_pending_messages
from socket_assignment.utils.protocol import parse , create_challenge_message, create_ack_message, create_download_response_tcp
from socket_assignment.security.auth import create_challenge, authentication_flow_server
from socket_assignment import connections, media, users
from socket_assignment.server import  disconnect_server
from socket_assignment.server.message_handling import handle_download_server,  check_message_is_reply


async def handle_direct_message_peer(peer_name,conn ,message):
   media = socket_assignment.media

   headers = message["headers"]
   reply_data = None
   if "sender" not in headers:
      raise ServerError(conn, message, "Missing sender header in MESSAGE frame!")
   
   if "data" not in message or not message["data"]:
      raise ServerError(conn, message, "Missing data MESSAGE frame!")

   if "mimetype" not in headers:
      raise ServerError(conn, message, "Must give a mimetype in headers.")

   sender = headers["sender"]
   data = message["data"]
   mimetype = headers["mimetype"]

   store_message_in_chat(sender, message, client_chats)
   store(peer_name, client_chats)

   if mimetype == "text/plain":
      print(f"\nNew message from {sender}!: {data.decode()}\n")
   else:
      if "filename" not in headers:
         raise ServerError(conn, message, "Must give a filename in headers.")
      mimetype = headers["mimetype"]
      filename = headers["filename"]
      media_id = add_new_media(peer_name,data, filename,mimetype, media)
      reply_data = media_id.encode()
      print(f"\n New file sent by {sender}!")

   ack_msg = create_ack_message(message, data=reply_data)
   await send_message(conn, ack_msg, awaitable=False)

@server_exceptions_handled
async def handle_message_peer(current_username,conn_id,message):
   # check if this is just a reply to a previous message, in which case
   # dont bother handling it, it will be handled anyway
   assert conn_id in connections

   conn = connections[conn_id]["connection"]

   if check_message_is_reply(conn, message):
      return

   # if this is a novel message sent by a connection
   command = message["command"]
   data = message["data"]
   headers = message["headers"]

   if command == "CONNECT":
      # begin authentication flow

      # find user
      # get from server if not found 
      await authentication_flow_server(current_username,conn_id, message, server_type="PEER")

      if "user_id" in connections[conn_id]:
         user_id = connections[conn_id]["user_id"]
         await send_pending_messages(user_id)
            
   elif command == "MESSAGE":
      await handle_direct_message_peer(current_username,conn, message)
      
   elif command == "DOWNLOAD":
      await handle_download_server(conn, server) 

   elif command == "DISCONNECT":
      # delete connections
      disconnect_server(conn_id)


# any Server exceptions thrown will be handled and send an error message back to the client
async def listen_peer(current_username,conn_id):
   conn = connections[conn_id]["connection"]
   try:
      async for message in recv_message(conn):
         # is this method
         asyncio.create_task( handle_message_peer(current_username,conn_id, message) )
   except ConnectionError as e:
      print(f"Error:{e}") 
   except BlockingIOError as be:
      print(f"Blocking Error:{be}")
   finally:
      if "user_id" in connections[conn_id]:
         print(f"Done with {connections[conn_id]["user_id"]}'s peer connection.")
      else:
         print(f"Done with connection {conn_id}")
      disconnect_server(conn_id)


def create_peer_socket_client(username):
   assert username in users
   peer_sock = create_socket()

   user_info = users[username]

   assert "ip" in user_info
   assert "port" in user_info
   assert "udp_port" in user_info

   conn_id  = str(uuid4())
   connections[conn_id] = { "connection": peer_sock, "user_id": username}
   user_info["connection_id"] = conn_id

   return conn_id



def bind_peer_socket():
   sock = create_socket()
   sock.bind(("0.0.0.0", 0))
   socket_assignment.peer.peer_tcp_port = sock.getsockname()[1]
   return sock


async def run_peer(current_username,sock):
   peer_tcp_port = socket_assignment.peer.peer_tcp_port

   sock.listen(100)
   print("Running tcp port", peer_tcp_port)

   try :
      async for conn, addr in get_connections(sock):
         conn_id = str(uuid4())

         connections[conn_id] = { "connection":conn} 

         asyncio.create_task(listen_peer(current_username,conn_id))

   except asyncio.CancelledError as e:
      print("cancelled peer")
   except Exception as e:
      print(e)
   except InterruptedError as e:
      print(e)
   finally:
      close(sock)