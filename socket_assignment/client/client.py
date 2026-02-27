import uuid
import asyncio
from socket_assignment.client import client_username, connections, server_connection, sending_queue, unacked_messages
from socket_assignment.utils.net import send, recvall
from socket_assignment.utils.protocol import parse , encode, message_to_text, text_to_message

def send_session(username):
    message_id = str(uuid.uuid4())
    connection  = connection["server"]
    token =connection["token"]
    sender = client_username 
    headers = {"message_no": message_id, "auth":token, "sender":client_username, "other":username}
    await send(conn, encode("SESSION", headers))

    text =await recvall(conn)

    command, headers, end = parse(text)

    if command == "SESSION":
        pass


async def client_sender(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    try :
        while True:
            message = await sending_queue.get()
            unacked_messages[message["message_id"]] = message
            send(conn, message_to_text(message).encode() )
    except ConnectionError as e:
        print(f"Error:{e}") 
    except BlockingIOError as be:
        print(f"Blocking Error:{be}")

# handle connection 
async def client_listener(conn_id):
    connection_info = connections[conn_id]
    conn = connection_info["connection"] 
    
    try:
        while True:
            data = await recvall(conn)
            data_str = data.decode()
            command, headers, data = parse(data_str) 
            handle_message(conn, command, headers, data)
            
    except ConnectionError as e:
      print(f"Error:{e}") 
    except BlockingIOError as be:
      print(f"Blocking Error:{be}")
    finally:
      print(f"Done with {conn.getsockname()}")
      close(conn)


