import socket

def recv_cstring(sock: socket.socket, encoding: str = 'utf-8') -> str:
    """
    Lee bytes del socket uno a uno hasta encontrar b'\0' o fin de flujo.
    Retorna la cadena decodificada (UTF-8 por defecto).
    """
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        # Si se cierra la conexión o no hay más datos, o encontramos '\0', paramos
        if not chunk or chunk == b'\0':
            break
        data.extend(chunk)
    return data.decode(encoding)