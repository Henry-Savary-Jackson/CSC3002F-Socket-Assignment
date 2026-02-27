# code for starting the peer server
# randomly choose ip, port

import socket
import asyncio
from socket_assignment.utils.net import create_socket ,get_connections, send, recvall, close
from socket_assignment.utils.protocol import parse 


async def handle_message(conn,command, headers, data=None):
   if command == "CONNECT":
      pass
   elif command == "AUTHENTICATE":
      pass
   elif command == "MESSAGE":
      pass
   elif command == "DOWNLOAD":
      pass
   elif command == "DISCONNECT":
      pass


async def peer_conn(conn):
   try:
        while True:
            data = await recvall(conn)
            data_str = data.decode()
            command, headers, data = parse(data_str) 
            handle_message(conn, command, headers, data)
            
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