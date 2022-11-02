import sys

from je_load_density import start_load_density_socket_server

try:
    server = start_load_density_socket_server()
    while not server.close_flag:
        pass
    else:
        sys.exit(0)
except Exception as error:
    print(repr(error))
