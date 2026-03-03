import asyncio
import base64
import random
from socket_assignment import unacked_messages, connections
from socket_assignment.utils.net import create_socket, send, udp_server
from socket_assignment.utils.protocol import create_session_message , parse_headers, message_to_bytes, bytes_to_message
from socket_assignment.storage import store_message_in_chat

server_connection = create_socket()
server_adress = "localhost"

udp_port =random.randrange(9000)

udp_socket = udp_server()

client_username =None 
client_signing_key = None
client_verifier_key = None

client_chats = dict()

pending_invites = []

