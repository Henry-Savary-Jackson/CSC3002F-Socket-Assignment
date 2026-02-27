# code for starting the peer server
# randomly choose ip, port

import socket
import asyncio
from socket_assignment.utils.net import create_socket ,get_connections, send, recvall, close, recv_message
from socket_assignment.client import users, unacked_messages
from socket_assignment.client.client import send_session
from socket_assignment.utils.protocol import parse , create_challenge_message
from socket_assignment.security.auth import create_challenge

async def handle_message_peer(conn,message):
   command = message["command"]
   data = message["data"]
   headers = message["headers"]
   if command == "CONNECT":
      # find user
      # get from server if not found 
      sender = headers["sender"]
      user = users[sender] if sender in users else None
      if not user:
         # get from server
         _, _ , public_key = await send_session(sender)
         # get challenge string
         # send 
         challenge = create_challenge()
         reponse = create_challenge_message()


   elif command == "AUTHENTICATE":
      pass
   elif command == "MESSAGE":
      mimetype = headers["mimetype"]
      if (mimetype == "text/plain"):
         print(data.decode())
      else:
         print("File")
   elif command == "DOWNLOAD":
      media_id = headers["media_id"]
      if "stream" in headers and headers["stream"]:
         pass 
      else:
         pass
   elif command == "DISCONNECT":
      close(conn) 

async def peer_conn(conn):
   try:
      async for message in recv_message(conn):
         # is this method
         handle_message_peer(conn, message) 
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
      asyncio.create_task(peer_conn(conn))