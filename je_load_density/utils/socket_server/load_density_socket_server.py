import json
import sys
from socket import AF_INET, SOCK_STREAM

import gevent
from gevent import monkey
from gevent import socket

from je_load_density.utils.executor.action_executor import execute_action


class TCPServer(object):

    def __init__(self):
        self.close_flag: bool = False
        self.server: socket.socket = socket.socket(AF_INET, SOCK_STREAM)

    def socket_server(self, host: str, port: int):
        self.server.bind((host, port))
        self.server.listen()
        while not self.close_flag:
            connection = self.server.accept()[0]
            gevent.spawn(self.handle, connection)
        sys.exit(0)

    def handle(self, connection):
        connection_data = connection.recv(8192)
        command_string = str(connection_data.strip(), encoding="utf-8")
        print("command is: " + command_string, flush=True)
        if command_string == "quit_server":
            connection.close()
            self.close_flag = True
            self.server.close()
            print("Now quit server", flush=True)
        else:
            try:
                execute_str = json.loads(command_string)
                if execute_str is not None:
                    for execute_return in execute_action(execute_str).values():
                        connection.send(str(execute_return).encode("utf-8"))
                        connection.send("\n".encode("utf-8"))
                    else:
                        connection.send("\n".encode("utf-8"))
                connection.send("Return_Data_Over_JE".encode("utf-8"))
                connection.send("\n".encode("utf-8"))
            except Exception as error:
                try:
                    connection.send(str(error).encode("utf-8"))
                    connection.send("\n".encode("utf-8"))
                    connection.send("Return_Data_Over_JE".encode("utf-8"))
                    connection.send("\n".encode("utf-8"))
                except Exception as error:
                    print(repr(error))
                    sys.exit(1)
            finally:
                connection.close()


def start_load_density_socket_server(host: str = "localhost", port: int = 9940):
    monkey.patch_all()
    server = TCPServer()
    server.socket_server(host, port)
    return server
