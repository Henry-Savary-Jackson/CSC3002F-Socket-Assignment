import asyncio

import functools
from socket_assignment.client import send_message
from socket_assignment.utils.protocol import create_error_message


class ServerError(Exception):
    """raise this when you encounter a message that causes an error."""
    def __init__(self,conn, original_message, cause ):
        super().__init__(cause)
        self.conn = conn
        self.original_message= original_message


def server_excpetions_handled(func):
    """Catches ServerError thrown by func, and sends an appropriate error message back to the client.
    You only use this on a function used to handle message on the central server or on the peer.
    If a client experiences an error, they would just print to console."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try :
            await func(*args, **kwargs)
        except ServerError as se:
            print(e)
            error_msg = create_error_message(e.original_message, e.message)
            send_message(e.conn, error_msg, awaitable=False)

    return wrapper