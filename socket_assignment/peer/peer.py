# code for starting the peer server
# randomly choose ip, port

import socket
import base64
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
      await handle_direct_message_peer(conn, message)
      
   elif command == "DOWNLOAD":
      if "media_id" not in headers:
         raise ServerError(conn, message, "Must specify media_id to download!")

      media_id = headers["media_id"]
      if "stream" in headers and headers["stream"]:
         # TODO: handle streaming
         await send_message(conn, create_ack_message(message),awaitable=False)
      else:
         if media_id not in media:
            raise ServerError(conn, message, "Media doesn't exist.")
         response =  create_download_response_tcp(messgae, media[media_id]) 
         await send_message(conn, response,awaitable=False)

   elif command == "DISCONNECT":
      close(conn) 


# any Server exceptions thrown will be handled and send an error message back to the client
async def listen_peer(conn):
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