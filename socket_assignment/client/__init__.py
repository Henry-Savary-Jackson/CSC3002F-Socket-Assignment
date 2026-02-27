import asyncio
from socket_assignment.utils.net import create_socket

server_connection = create_socket()
server_adress = "localhost"

sending_queue = asyncio.Queue() 
unacked_messages = dict()

client_username = ""

connections = dict()
users = dict() 
# for each  user, store ip, addr, connection id, public_key