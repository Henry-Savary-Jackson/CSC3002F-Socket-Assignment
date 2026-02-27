import uuid
import asyncio
from socket_assignment.client import client_username, connections, server_connection, sending_queue, unacked_messages
from socket_assignment.utils.net import send, recv_message

from socket_assignment import users
from socket_assignment.server import VALID_COMMANDS_PEER
from socket_assignment.utils.protocol import parse, parse_headers , encode,message_to_bytes, bytes_to_message, create_message

def send_session(username):
    message_id = str(uuid.uuid4())
    connection_info  = connections["server"]
    token =connection_info["token"]
    sender = client_username 

    headers = {"message_no": message_id, "auth":token, "sender":client_username, "other":username}

    message = create_message("SESSION", headers)

    response_message = await send_message(connection_info["conn"], message)

    # get the info from message body
    info = parse_headers(response_message["data"].decode().split())

    ip = info["ip"]
    addr = info["addr"]
    pub_key = info["public_key"]
    if username in users:
        users[username].update(info)
    else:
        users[username] = info
    return ip, addr, pub_key


def send_message(conn ,message):
    future =  asyncio.get_event_loop().create_future()
    unacked_messages[message["message_id"]] = {"message":message, "future":future}
    try :
        send(conn,message_to_text(message))
    except:
        pass
    finally:
        return future


def handle_message_client(conn, message):
    command = message["command"]
    message_id = message["message_id"]
    if message_id in unacked_messages:
        # notify waiting functions
        future = unacked_messages[message_id]["future"]
        future.set_result(message)
        del unacked_messages[message_id]

    if command == "ACK":
        pass
    if command == "CHALLENGE":
        pass
        

# handle connection 
async def client_listener(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    
    try:
        async for message in recv_message:
            handle_message_client(conn, message)
            
    except ConnectionError as e:
      print(f"Error:{e}") 
    except BlockingIOError as be:
      print(f"Blocking Error:{be}")
    finally:
      print(f"Done with {conn.getsockname()}")
      close(conn)


