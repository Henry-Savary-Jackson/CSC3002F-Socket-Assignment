import socket
import asyncio

BUF_SIZE = 4096
MAX_CONN = 100
SERVER_PORT = 5000

async def recvall(conn):
    "Collect all the chunks of data  of size BUF_SIZE until the final one is received."
    full_data= bytearray()
    async for data in recv(conn):
        full_data.extend(data)
        if len(data) < BUF_SIZE:
            break
    return full_data

def create_socket():
    return socket.socket()
    

def bind_server(sock, port):
    sock.bind(("0.0.0.0",port))

def connect(sock, address, port):
    sock.connect((address, port))

def listen(sock):
    sock.listen(MAX_CONN)

def close(sock):
    sock.close()

async def get_connections(sock):
    "Asynchronously accepts all incoming connections. Other function can iterate over this function to get all the incoming connections and handle the,"
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


