import asyncio
import base64
from socket_assignment import unacked_messages
from socket_assignment.utils.net import create_socket, send, udp_server
from socket_assignment.utils.protocol import create_session_message , parse_headers

server_connection = create_socket()
server_adress = "localhost"

udp_socket = udp_server()

client_username =None 
client_public_key_b64 = None
client_private_key_b64 = None

async def send_message(conn ,message, awaitable=True):
    """Given a socket, send this message to this socket
    
    awaitable is used to indicate if you will call await on this function
    in order to await the response from the socket.
    If you are not waiting for a response from sending this message, set awaitable to False
    """
    future =  asyncio.get_event_loop().create_future() if awaitable else None

    # keep track of this message as not yet receiving a reply
    # schedule the sending of data to event-loop
    try :
        if awaitable:
            unacked_messages[message["message_id"]] = {"message":message, "future":future}
        await send(conn,message_to_text(message))
        if future:
            return await future
    except Exception:
        if awaitable:
            unacked_messages.pop(message["message_id"])
        raise  

    # this returns a future, so that the caller can await the response from the remote connection

# for each  user, store ip, addr, connection id, public_key
async def send_session(username):
    connection_info  = connections["server"]
    token =connection_info["token"]

    message = create_session_message(username, client_username, token)

    response_message = await send_message(connection_info["connection"], message)

    # get the info from message body
    info = parse_headers(response_message["data"].decode().split())

    if username in users:
        # update this user with this information
        users[username].update(info)
    else:
        users[username] = info
    return info["ip"], info["port"], info["public_key"] 


