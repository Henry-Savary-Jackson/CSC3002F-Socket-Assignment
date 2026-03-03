
from socket_assignment.client.client import run_client, client_listener
from socket_assignment.server.server import run_server, close 
from socket_assignment.server import server_sock
import asyncio

if __name__ == "__main__":
    program_type = input("Server(S)/Client(C)?:\n").upper()[:1]
    if program_type == "C":
        asyncio.run(run_client())
    elif program_type == "S":
        try:
            asyncio.run(run_server())
        except InterruptedError:
            close(server_sock)