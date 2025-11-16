import json
import sys
from socket import AF_INET, SOCK_STREAM
from typing import Any

import gevent
from gevent import monkey
from gevent import socket

from je_load_density.utils.executor.action_executor import execute_action


class TCPServer:
    """
    基於 gevent 的 TCP 伺服器
    TCP server based on gevent

    - 接收 JSON 指令並執行對應動作
    - 支援 "quit_server" 指令來關閉伺服器
    """

    def __init__(self) -> None:
        self.close_flag: bool = False
        self.server: socket.socket = socket.socket(AF_INET, SOCK_STREAM)

    def socket_server(self, host: str, port: int) -> None:
        """
        啟動伺服器
        Start the TCP server

        :param host: 伺服器主機位址 (Server host)
        :param port: 伺服器埠號 (Server port)
        """
        self.server.bind((host, port))
        self.server.listen()
        print(f"Server started on {host}:{port}", flush=True)

        while not self.close_flag:
            try:
                connection, _ = self.server.accept()
                gevent.spawn(self.handle, connection)
            except Exception as error:
                print(f"Server error: {error}", file=sys.stderr)
                break

        self.server.close()
        print("Server shutdown complete", flush=True)

    def handle(self, connection: socket.socket) -> None:
        """
        處理單一連線
        Handle a single connection

        :param connection: 客戶端連線 (Client connection)
        """
        try:
            connection_data = connection.recv(8192)
            if not connection_data:
                return

            command_string = connection_data.strip().decode("utf-8")
            print(f"Command received: {command_string}", flush=True)

            if command_string == "quit_server":
                self.close_flag = True
                connection.send(b"Server shutting down\n")
                print("Now quit server", flush=True)
            else:
                try:
                    execute_str: Any = json.loads(command_string)
                    if execute_str is not None:
                        for execute_return in execute_action(execute_str).values():
                            connection.send(f"{execute_return}\n".encode("utf-8"))
                    connection.send(b"Return_Data_Over_JE\n")
                except Exception as error:
                    connection.send(f"Error: {error}\n".encode("utf-8"))
                    connection.send(b"Return_Data_Over_JE\n")

        finally:
            connection.close()


def start_load_density_socket_server(host: str = "localhost", port: int = 9940) -> TCPServer:
    """
    啟動 LoadDensity TCP 伺服器
    Start LoadDensity TCP server

    :param host: 主機位址 (Host)
    :param port: 埠號 (Port)
    :return: TCPServer 實例 (TCPServer instance)
    """
    monkey.patch_all()
    server = TCPServer()
    server.socket_server(host, port)
    return server