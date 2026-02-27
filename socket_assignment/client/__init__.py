import asyncio
from socket_assignment.utils.net import create_socket

server_connection = create_socket()
server_adress = "localhost"

client_username =None 
client_public_key_bytes = None
client_private_key_bytes = None

#
# for each  user, store ip, addr, connection id, public_key