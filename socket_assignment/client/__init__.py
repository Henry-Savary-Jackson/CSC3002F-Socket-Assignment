from collections import deque
from socket_assignment.utils.net import create_socket

server_connection = create_socket()
server_adress = "localhost"

sending_queue = deque()

client_username = ""

connections = dict()
users = dict() 
# for each  user, store ip, addr, connection id, public_key