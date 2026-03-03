
import random
from uuid import uuid4
import nacl 
import base64
from socket_assignment import users, connections
from socket_assignment.client.client_sending import send_session, send_message
from socket_assignment.utils.net import connect, create_socket
from socket_assignment.utils.protocol import create_message, AUTH_TOKEN_HEADER_NAME,create_challenge_message, create_authentication_message, create_session_message, create_ack_message, create_error_message, create_connect_message
from socket_assignment.utils.exceptions import ServerError

CHALLENGE_SIZE = 128
TOKEN_SIZE = 128

def generate_keypair():
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    return signing_key, verify_key

def create_challenge():
    return base64.b64encode(random.randbytes(CHALLENGE_SIZE))

def get_auth_token():
    return base64.b64encode(random.randbytes(TOKEN_SIZE))

async def authentication_flow_server(conn_id,connect_msg, server_type="SERVER"):
    
    conn = connections[conn_id]["connection"]

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

        user["connection_id"] = conn_id  # link the user to its connections
        
        # store info about this connection in order to be used later
        connections[conn_id].update({
            "user_id":sender,
            "token": token.decode()

        })

        success_response = create_ack_message(authenticate_msg, token=token.decode())
        await send_message(conn, success_response, awaitable=False)

    except nacl.exceptions.BadSignatureError as e:
        print("Bad signature, failed!")
        raise ServerError(conn, authenticate_msg, "Invalid Signature!")


async def authenticate_flow_client(conn_id, username, signing_key, verify_key, peer_tcp_port, udp_port):
    conn = connections[conn_id]["connection"]
    public_key_b64 = verify_key.encode(encoder=nacl.encoding.Base64Encoder).decode()
    connect_msg = create_message("CONNECT", headers={
        "sender": username,
        "public_key": public_key_b64,
        "ip": "127.0.0.1",
        "port": peer_tcp_port,
        "udp_port": udp_port
    })
    challenge_msg = await send_message(conn, connect_msg, awaitable=True)
    print("Received challenge",challenge_msg)
    if challenge_msg["command"] != "CHALLENGE":
        print("Expected CHALLENGE, got", challenge_msg["command"])
        return False
    challenge_data = challenge_msg["data"]
    signature = signing_key.sign(challenge_data)
    auth_msg = create_message("AUTHENTICATE", headers={"sender": username},
                              data=signature, reply=challenge_msg["message_id"])
    ack = await send_message(conn, auth_msg, awaitable=True)
    if ack["command"] == "ACK":

        token = ack["headers"][AUTH_TOKEN_HEADER_NAME]
        connections[conn_id]["client_token"]  = token
        print("Authentication successful")
        return True
    else:
        print("Authentication failed")
        return False

async def connect_to_peer(username, client_username, signing_key,verify_key, user_tcp_port, user_udp_port):
    assert username in users

    peer_sock = create_socket()

    user_info = users[username]

    assert "ip" in user_info
    assert "port" in user_info
    assert "udp_port" in user_info


    tcp_port = user_info["port"]
    udp = user_info["udp_port"]


    await connect(peer_sock, user_info["ip"], user_info["port"])
    conn_id  = str(uuid4())
    connections[conn_id] = { "connection": peer_sock, "user_id": username}
    result = await authenticate_flow_client(conn_id, client_username,signing_key, verify_key, user_tcp_port, user_udp_port )
    if not result:
        del connections[conn_id]
        return None

    user_info["connection_id"] = conn_id

    return conn_id
    # start listening as a peer on this new socket

