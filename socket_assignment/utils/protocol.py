import base64
from uuid import uuid4
from nacl.signing import SigningKey, VerifyKey
import socket


AUTH_TOKEN_HEADER_NAME = "auth"
MESSAGE_ID_HEADER_NAME = "message_no"
REPLY_HEADER_NAME = "reply_to"


def parse_headers(lines):
    """given the lines of headers in format
    key1:value1
    vconvert them into a python dictionary
    """
    headers = dict()
    try :
        for line in lines:
            key, value = line.split(":")
            headers[key] = value
    except ConnectionError as e:
        print(f"Error:{e}") 
    except BlockingIOError as be:
        print(f"Blocking Error:{be}")
    finally:
        return headers 

def parse(data_bytes):
    "Parses the text data received from a socket into its command, headers and data."

    lines = data_bytes.decode().split("\n")
    assert len(lines) >= 4
    command = lines[0]

    header_lines = []
    cur_line = 2
    while cur_line < len(lines):
        if not lines[cur_line]:
            break
        cur_line+=1
    header_lines = lines[2:cur_line]

    headers = parse_headers(header_lines)

    data = bytes()
    for i in range(cur_line+1, len(lines)):
        data += base64.b64decode(lines[i])

    return command, headers, data

def encode(command, headers, data=None):
    "Used to encode a mesage,its headers and data into text to be sent over a socket"

    headers_text = "\n".join([ f"{key}:{value}" for key,value in headers.items() ])

    b64_data =base64.b64encode(data).decode() if data else ""

    message_bytes =f"{command.upper()}\n\n{headers_text}\n\n{b64_data}".encode()
    
    return len(message_bytes).to_bytes(4, byteorder="big") + message_bytes

def create_message(command,headers=None, data=None,reply=None,token=None):
    """Create a message object with the given parameters.

    reply is the id of the message this message is reply to. Only give this if this is a reply to another message.
    otherwise, leave this None.

    token is used for requests that need authentication, such as MESSAGE or INVITE
    """

    headers = headers or dict()

    output = {"command":command, "headers":headers  }
    if reply:
        headers[REPLY_HEADER_NAME] = reply
    if token:
        headers[AUTH_TOKEN_HEADER_NAME] = token

    output["message_id"] = str(uuid4())
    headers[MESSAGE_ID_HEADER_NAME] = output["message_id"]

    if data:
        output["data"] =data
    
    return output

def message_to_bytes(message):
    return encode(message["command"], message["headers"], message["data"] if "data" in message else None )

def bytes_to_message(data_bytes):
    command, headers, data = parse(data_bytes) 
    return {"message_id":headers[MESSAGE_ID_HEADER_NAME], "headers":headers, "data":data, "command":command}

def create_connect_message(sender, public_key=None, ip=None, tcp_port=None,udp_port=None):
    headers = {"sender":sender}
    if ip:
        headers["ip"] = ip
    if tcp_port:
        headers["port"] = tcp_port
    if udp_port:
        headers["udp_port"] = udp_port
    if public_key:
        headers["public_key"] = public_key
    return create_message("CONNECT", headers) 

def create_session_message(other_user,current_user, token):
    headers = {"sender":current_user, "other":other_user}
    return create_message("SESSION", headers, token=token)

def create_challenge_message(original,challenge):
    headers = {"sender": original["headers"]["sender"]  }
    return create_message("CHALLENGE", headers, data, reply=original["message_id"])

def create_authentication_message(challenge_msg,private_key:SigningKey, sender):
    signature = private_key.sign(challenge_msg)
    headers = {"sender":sender}
    return create_message("AUTHENTICATE", headers, signature, reply=challenge_msg["message_id"])

def create_ack_message(original_message, **kwargs):
    return create_message("ACK",  reply=original_message["message_id"], **kwargs)

def create_error_message(original, cause):
    headers = {"explanation":cause}
    return create_message("ERROR", headers, data)

def create_join_message(original, chat_id):
    return create_message("JOIN", {})

def create_download_response_tcp(original, media):
    data = base64.b64decode(media["data"])
    headers = {"content_length" :len(data), "mimetype":media["mimetype"], "filename":media["filename"]}
    return create_ack_message(original, data=data,headers=headers)
