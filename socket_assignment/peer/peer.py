# code for starting the peer server
# randomly choose ip, port

import socket
import base64
from socket_assignment.peer import peer_tcp_port
from uuid import uuid4
import asyncio
from socket_assignment.utils.exceptions import server_excpetions_handled, ServerError
from socket_assignment.storage import add_new_media
from socket_assignment.utils.net import create_socket ,get_connections, send, recvall, close, recv_message
from socket_assignment.client import users, unacked_messages, send_message
from socket_assignment.client.client import send_session, check_message_is_reply 
from socket_assignment.utils.protocol import parse , create_challenge_message, create_ack_message, create_download_response_tcp
from socket_assignment.security.auth import create_challenge, authentication_flow_server
from socket_assignment import connections, media
from socket_assignment.server import handle_download_server, disconnect_server, send_pending_messages


async def handle_direct_message_peer(conn ,message):
   headers = message["headers"]
   reply_data = None
   if (mimetype == "text/plain"):
      print(f"New message {data.decode()}")
   else:
      if "filename" not in headers:
         raise ServerError(conn, message, "Must give a filename in headers.")
      if "mimetype" not in headers:
         raise ServerError(conn, message, "Must give a mimetype in headers.")
      mimetype = headers["mimetype"]
      filename = headers["filename"]
      media_id = add_new_media(data, filename,mimetype)
      reply_data = media_id.encode()

   ack_msg = create_ack_message(message, data=reply_data)
   await send_message(conn, ack_msg, awaitable=False)



@server_excpetions_handled
async def handle_message_peer(conn_id,message):
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
      await authentication_flow_server(conn, message, server_type="PEER")

      if "user_id" in connections[conn_id]:
         user_id = connections[conn_id]["user_id"]
         await send_pending_messages(user_id)
            
   elif command == "MESSAGE":
      await handle_direct_message_peer(conn, message)
      
   elif command == "DOWNLOAD":
      await handle_download_server(conn, server) 

   elif command == "DISCONNECT":
      # delete connections
      disconnect_server(conn_id)


# any Server exceptions thrown will be handled and send an error message back to the client
async def listen_peer(conn_id):
   conn = connections[conn_id]["connection"]
   try:
      async for message in recv_message(conn):
         # is this method
         await handle_message_peer(conn_id, message) 
   except ConnectionError as e:
      print(f"Error:{e}") 
   except BlockingIOError as be:
      print(f"Blocking Error:{be}")
   finally:
      print(f"Done with {conn.getsockname()}")
      close(conn)



async def run_peer():
   global peer_tcp_port
   sock = create_socket()
   sock.bind(("0.0.0.0", peer_tcp_port))
   sock.listen(100)

   async for conn, addr in get_connections(sock):
      conn_id = str(uuid4())
      connections[conn_id] = { "connection":conn} 
      asyncio.create_task(listen_peer(conn_id))