
from socket_assignment.client.client import main
from socket_assignment.server.server import run_server
import asyncio

if __name__ == "__main__":
    program_type = input("Server(S)/Client(C)?:\n").upper()
    if program_type == "C":
        asyncio.run(main())
    
    else:
        asyncio.run(run_server())
        print("Invalid input.")


    # program_type = input("Server(S)/Client(C)?:\n").upper()
    # if program_type == "C":
    #     pass
    # elif program_type =="S":
    #     pass
    # else:
    #     print("Invalid input.")