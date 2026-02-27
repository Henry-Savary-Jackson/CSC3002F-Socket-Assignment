import base64


def parse_headers(lines):
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

def parse(text):
    "Parses the text data received from a socket into its command, headers and data."
    lines = text.split("\n")
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

    text =f"{command.upper()}\n\n{headers_text}\n\n{b64_data}" 
    
    return text

def message_to_text(message):
    return encode(message["command"], message["headers"], message["data"])

def text_to_message(text):
    command, headers, data = parse(text) 
    return {"message_id":headers["message_no"], "headers":headers, "data":data, "command":command}