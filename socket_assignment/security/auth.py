
import random
import base64

CHALLENGE_SIZE = 128
TOKEN_SIZE = 128

def create_challenge():
    return base64.b64encode(random.randbytes(CHALLENGE_SIZE))

def get_auth_token():
    return base64.b64decode(random.randbytes(TOKEN_SIZE))
