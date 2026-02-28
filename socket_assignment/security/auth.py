
import random
from uuid import uuid4
import nacl
import base64
from socket_assignment import users, connections
from socket_assignment.client import send_session, send_message
from socket_assignment.utils.protocol import create_challenge_message , create_session_message, create_ack_message, create_error_message
from socket_assignment.utils.exceptions import ServerError

CHALLENGE_SIZE = 128
TOKEN_SIZE = 128

def create_challenge():
    return base64.b64encode(random.randbytes(CHALLENGE_SIZE))

def get_auth_token():
    return base64.b64decode(random.randbytes(TOKEN_SIZE))

async def authentication_flow_server(conn,connect_msg, server_type="SERVER"):
    headers = connect_msg["headers"]
    assert "sender" in headers 
    sender = headers["sender"]
    if sender not in users and server_type == "SERVER":

        if "public_key" not in  headers:
            raise ServerError(conn, connect_msg, """User doesn't exist and no public key was provided.
             If you are trying to create a new account, include the public key.""")
            
        public_key_b64  =  headers["public_key"]

        ip = headers["ip"]

        port = int(headers["port"])

        users[sender] = { "public_key":public_key_b64, "username":sender, "ip": ip, "port":port}
        # get from server

        # create new user
    elif server_type == "PEER":
        ip, port, public_key = await send_session(sender)

    user = users[sender] 

    challenge = create_challenge()
    challenge_msg = create_challenge_message(connect_msg,challenge)
    authenticate_msg = await send_message(conn, challenge_msg)

    data = authenticate_msg["data"]
    assert data 

    # create a public key used to verify this user's signature
    verifier_key = nacl.signing.VerifyKey(user["public_key"], nacl.encoding.Base64Encoder)
    try :
        # verify signature
        original = verifier_key.verify(base64.b64decode(data))

        #sucessfully veirified
        token = get_auth_token()
        # create connection object
        connection_id = uuid4()

        user["connection_id"] = connection_id  # link the user to its connections
        
        # store info about this connection in order to be used later
        connections[connection_id] = {
            "connection":conn,
            "user_id":sender,
            "token": base64.b64encode(token)
        } 

        success_response = create_ack_message(authenticate_msg, token)
        send_message(conn, success_response, awaitable=False)

    except nacl.exceptions.BadSignatureError as e:
        print("Bad signature, failed!")
        raise ServerError(conn, authenticate_msg, "Invalid Signature!")

        
    
