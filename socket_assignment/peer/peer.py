# code for starting the peer server
# randomly choose ip, port

import socket
import asyncio
from socket_assignment.utils.exceptions import server_excpetions_handled
from socket_assignment.utils.net import create_socket ,get_connections, send, recvall, close, recv_message
from socket_assignment.client import users, unacked_messages, send_message
from socket_assignment.client.client import send_session  
from socket_assignment.utils.protocol import parse , create_challenge_message, create_ack_message
from socket_assignment.security.auth import create_challenge, authentication_flow_server
from socket_assignment import connections

@server_excpetions_handled
async def handle_message_peer(conn,message):
   # check if this is just a reply to a previous message, in which case
   # dont bother handling it, it will be handled anyway
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
      
   elif command == "MESSAGE":
      mimetype = headers["mimetype"]
      ack_msg = create_ack_message(message)
      send_message(conn, ack_msg, awaitable=False)
      if (mimetype == "text/plain"):
         print(data.decode())
      else:
         print("File")

   elif command == "DOWNLOAD":
      media_id = headers["media_id"]
      if "stream" in headers and headers["stream"]:
         # handle streaming
         pass 
      else:
         pass
   elif command == "DISCONNECT":
      close(conn) 


# any Server exceptions thrown will be handled and send an error message back to the client
async def listen_peer(conn_id):
   conn = connections[conn_id]["connection"]

   assert conn

   try:
      async for message in recv_message(conn):
         # is this method
         await handle_message_peer(conn, message) 
   except ConnectionError as e:
      print(f"Error:{e}") 
   except BlockingIOError as be:
      print(f"Blocking Error:{be}")
   finally:
      print(f"Done with {conn.getsockname()}")
      close(conn)



async def run_peer(port):
   sock = create_socket()
   sock.bind(("0.0.0.0", port))
   sock.listen(100)

   async for conn, addr in get_connections(sock):
      asyncio.create_task(listen_peer(conn))