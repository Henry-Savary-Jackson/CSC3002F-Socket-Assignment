
from socket_assignment.client.client import main, client_listener
from socket_assignment.server.server import run_server
import asyncio

if __name__ == "__main__":
    program_type = input("Server(S)/Client(C)?:\n").upper()[:1]
    if program_type == "C":
        asyncio.run(main())
    elif program_type == "S":
        asyncio.run(run_server())