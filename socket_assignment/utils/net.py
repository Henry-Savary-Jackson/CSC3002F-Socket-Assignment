import socket
import asyncio

BUF_SIZE = 4096
MAX_CONN = 100
SERVER_PORT = 5000

async def recvall(conn):
    full_data= bytearray()
    async for data in recv(conn):
        full_data.extend(data)
        if len(data) < BUF_SIZE:
            break
    return full_data

def create_socket():
    sock = socket.socket()
    return sock

def bind_server(sock):
    sock.bind(("localhost",SERVER_PORT))

def connect(sock, address, port):
    sock.connect((address, port))

def listen(sock):
    sock.listen(MAX_CONN)

def close(sock):
    sock.close()

async def get_connections(sock):
    while True:
        conn,address =  sock.accept()
        conn.setblocking(False)
        yield conn, address

async def recv(conn):
    while True:
        data =  conn.recv(BUF_SIZE)
        yield data

async def send(conn,data:str):
    conn.send(data)


