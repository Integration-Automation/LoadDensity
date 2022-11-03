from je_load_density.utils.socket_server.load_density_socket_server import start_load_density_socket_server

try:
    server = start_load_density_socket_server()
except Exception as error:
    print(repr(error))
