import socket
import asyncio
from socket_assignment.utils.protocol import bytes_to_message

BUF_SIZE = 4096
MAX_CONN = 100
SERVER_PORT = 5000

async def recv_message(conn):
    async for message_bytes in recvall(conn):
        yield bytes_to_message(message_bytes)

async def recvall(conn):
    "Continously gives the bytes of the next message."
    while True:
        length_data  = await recv(conn ,4)
        if length_data is None:
            break
        length = int.from_bytes(length_data, byteorder="big")
        data =   await recv(conn ,length)
        if data is None:
            break
        yield data

def create_socket():
    return socket.socket()
    

def bind_server(sock, port):
    sock.bind(("0.0.0.0",port))

async def connect(sock, address, port):
    sock.setblocking(False)
    await asyncio.get_event_loop().sock_connect(sock, (address, port))

def listen(sock):
    sock.listen(MAX_CONN)

def close(sock):
    sock.close()

async def get_connections(sock):
    "Asynchronously accepts all incoming connections. Other function can iterate over this function to get all the incoming connections and handle the,"
    while True:
        conn,address = await asyncio.get_event_loop().sock_accept(sock)
        conn.setblocking(False)
        yield conn, address

async def recv(conn, n):
    "Asynchornously gives the next chunk of data from a tcp socket. "
    data = await asyncio.get_event_loop().sock_recv(conn, n)
    if not data:
        return None
    return data

        

async def send(conn,data):
    print("Sending...")
    await asyncio.get_event_loop().sock_sendall(conn, data)

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    return sock

async def async_udp_client():
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.setblocking(False)
    return  client_socket

async def recv_udp(sock):
    await asyncio.get_event_loop().sock_recvfrom(sock, BUF_SIZE )
