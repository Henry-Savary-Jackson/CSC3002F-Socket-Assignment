
import random
from uuid import uuid4
import nacl 
import base64
from socket_assignment import users, connections
from socket_assignment.client import send_session, send_message, client_public_key_b64, client_private_key_b64
from socket_assignment.utils.protocol import create_challenge_message, create_authentication_message, create_session_message, create_ack_message, create_error_message, create_connect_message
from socket_assignment.utils.exceptions import ServerError

CHALLENGE_SIZE = 128
TOKEN_SIZE = 128

def create_challenge():
    return base64.b64encode(random.randbytes(CHALLENGE_SIZE))

def get_auth_token():
    return base64.b64encode(random.randbytes(TOKEN_SIZE))

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

        udp_port = int(headers["udp_port"])

        users[sender] = { "public_key":public_key_b64, "username":sender, "ip": ip, "port":port, "udp_port":udp_port}
        # get from server

        # create new user
    elif server_type == "PEER":
        ip, port, public_key = await send_session(sender)


    user = users[sender] 

    if "connection_id" in user and user["connection_id"]:
        # simply reply
        connection_info = connections[user["connection_id"]]
        assert "token" in connection_info
        token =  connection_info["token"]
        ack_response =create_ack_message(connect_msg, base64.b64decode(token)) 
        await send_message(conn,ack_response,awaitable=False)
        return

    challenge = create_challenge()
    challenge_msg = create_challenge_message(connect_msg,challenge)
    authenticate_msg = await send_message(conn, challenge_msg)

    data = authenticate_msg["data"]
    assert data 

    # create a public key used to verify this user's signature
    verifier_key = nacl.signing.VerifyKey(user["public_key"], nacl.encoding.Base64Encoder)
    try :
        # verify signature
        original = verifier_key.verify(data)

        #sucessfully veirified
        token = get_auth_token()
        # create connection object
        connection_id = uuid4()

        user["connection_id"] = connection_id  # link the user to its connections
        
        # store info about this connection in order to be used later
        connections[connection_id] = {
            "connection":conn,
            "user_id":sender,
            "token": token.decode()
        } 

        success_response = create_ack_message(authenticate_msg, token=token.decode())
        await send_message(conn, success_response, awaitable=False)

    except nacl.exceptions.BadSignatureError as e:
        print("Bad signature, failed!")
        raise ServerError(conn, authenticate_msg, "Invalid Signature!")


async def create_keypair():
    signing_key = nacl.signing.SigningKey.generate()
    private_key = signing_key.encode(nacl.encoding.Base64Encoder)
    public_key = signing_key.verify_key.encode(nacl.encoding.Base64Encoder)
    return private_key, public_key
        
    
async def authentication_flow_client(conn_id,conn,username, ip, port_tcp, port_udp, private_key, public_key=None ):
    connect_msg = create_connect_message(username, ip=ip, tcp_port=port_tcp, udp_port=port_udp, public_key=public_key)
    reply = await send_message(conn, connect_msg)
    if reply["command"] == "ERROR":
        raise Exception(f"Failed to connect:{resp_cmd["headers"]["cause"]}")
    challenge_msg = reply

    signing_key = nacl.signing.SigningKey(private_key, nacl.encoding.Base64Encoder)

    auth_msg = create_authentication_message(challenge_msg, signing_key) 

    response = await send_message(conn, auth_msg)

    resp_cmd = response["command"] 
    if resp_cmd == "ACK":
        token = base64.b64decode(response["data"]).decode()
        connections[conn_id] = {"connection":conn,"token":token}
    elif resp_cmd == "ERROR":
        raise Exception(f"Failed to connect:{resp_cmd["headers"]["cause"]}")

    
