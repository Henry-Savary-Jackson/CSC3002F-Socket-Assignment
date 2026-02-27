import uuid
from socket_assignment.client import client_username, connections, server_connection
from socket_assignment.utils.net import send, recvall
from socket_assignment.utils.protocol import parse , encode

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

