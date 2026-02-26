import socket
import asyncio
from socket_assignment.utils.net import create_socket, close, recvall, get_connections , send,listen, connect, SERVER_PORT, BUF_SIZE

async def main():
    sock = create_socket()
    try :
        connect(sock, "localhost",SERVER_PORT )
        s = "Hello"*4000
        await send(sock,s.encode())
        await send(sock,"\nfjj".encode())
        await send(sock,"\nhe".encode())
        await send(sock,"\nfk".encode())
        await send(sock,"\n44444edde".encode())

        while True:
            response = await recvall(sock)
            print(f"Data from server:{response.decode()}")
            if (len(response)<BUF_SIZE):
                break


    except ConnectionRefusedError:
        print("The connection to the server was refused")
    finally:
        close(sock)

if __name__ == "__main__":
    # run the event loop, schedule this main function to execute in event loop
    asyncio.run(main())


