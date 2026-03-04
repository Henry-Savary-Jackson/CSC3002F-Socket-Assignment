import asyncio
import base64
import random
from socket_assignment import unacked_messages, connections
from socket_assignment.utils.net import create_socket, send, udp_server
from socket_assignment.utils.protocol import create_session_message , parse_headers, message_to_bytes, bytes_to_message
from socket_assignment.storage import store_message_in_chat

server_connection = create_socket()
server_adress = "localhost"

udp_port = None

udp_socket = udp_server()

client_username =None  # global variable for username
client_signing_key = None # this is supposed to be a nacl.signing.SigningKey
client_verifier_key = None # this is supposed to be a nacl.signing.SigningKey

pending_invites = [] # sglobal variable tores all the pending invites the client has received

