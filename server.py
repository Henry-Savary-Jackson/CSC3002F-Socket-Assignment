
import socket
import asyncio
from socket_assignment.utils.net import create_socket, close, recvall, get_connections , send,listen, bind_server


async def echo(conn):
    try:
        while True:
            print("waiting...")
            data = await recvall(conn)
            data_str = data.decode()
            print(f"Data: {data_str}")
            print("sending...")
            await send(conn, data_str.upper().encode())
            
    except ConnectionError as e:
        print(f"Error:{e}") 
    except BlockingIOError as be:
        print(f"Blocking Error:{be}")
    finally:
        print(f"Done with {conn}")
        close(conn)

async def main():
    sock = create_socket()
    bind_server(sock)

    listen(sock)
    try :
        async for conn, address in get_connections(sock):
            print(f"connected from address: {address}")
            # shcedule an asynchronous task to handle data from each new connection
            # asyncio will juggle all of these concurrent connections
            await asyncio.create_task(echo(conn))
    finally:
        print("\nDeleting socket...")
        close(sock)


if __name__ == "__main__":
    try :
        # run the event loop, schedule this main function to execute in event loop
        asyncio.run(main());
    except KeyboardInterrupt:
        print("Admin shutting down server...")
    finally:
        print("Shut down server")