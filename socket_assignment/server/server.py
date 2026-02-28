
import socket
import asyncio
from socket_assignment.utils.net import create_socket ,get_connections, send,recv_message, close
from socket_assignment.utils.protocol import parse 
from socket_assignment.security.auth import  authentication_flow_server 
from socket_assignment.utils.exceptions import  server_excpetions_handled 
from socket_assignment.client.client import check_message_is_reply

@server_excpetions_handled
async def handle_message_main_server(conn,message):
   if check_message_is_reply(conn , message):
      return

   command = message["command"]
   if command == "CONNECT":
      await authentication_flow_server(conn, message)
   elif command == "DOWNLOAD":
      pass
   elif command == "INVITE":
      pass
   elif command == "JOIN":
      pass
   elif command == "REJECT":
      pass
   elif command == "DISCONNECT":
      close(conn)


async def handle_new_conn(conn):
   try:
      async for message in recv_message(conn):
         await handle_message_main_server(conn,message )
            
   except ConnectionError as e:
      print(f"Error:{e}") 
   except BlockingIOError as be:
      print(f"Blocking Error:{be}")
   finally:
      print(f"Done with {conn.getsockname()}")
      close(conn)
