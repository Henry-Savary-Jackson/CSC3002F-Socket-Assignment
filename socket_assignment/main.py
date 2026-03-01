from socket_assignment.client import client_username, server_connection, client_private_key_b64, client_public_key_b64
from socket_assignment.client.client import client_listener
import asyncio
from socket_assignment.peer.peer import run_peer 
from socket_assignment.security.auth import  authentication_flow_client, create_keypair

if __name__ == "__main__":

    program_type = input("Server(S)/Client(C)?:\n").upper()
    if program_type == "C":
        client_username = input("Username?:\n")

                
    elif program_type =="S":
        pass
    else:
        print("Invalid input.")


def start_as_client(username):
    port = 4444
    asyncio.create_task(run_peer(port))

    port_udp = 5555

    # connect server
    server_id = "server"

    client_private_key_b64, client_public_key_b64 =  create_keypair()

    try :
        await authentication_flow_client(server_id,server_connection, client_username,\
            "localhost", port, port_udp, client_private_key_b64, client_public_key_b64  )
        
        asyncio.create_task(client_listener(server_id))
        print("Connected to server")
        while True:
            next_action = input("(Q)uit/(M)essage/(D)irect?:\n").upper()
            if next_action == "Q":
                break 
            elif next_action == "M":
                # TODO: send message
                pass
            elif next_action == "D":
                pass
            
    except Exception as e :
        print(e)
